import subprocess
import sys
from pathlib import Path

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from joblib import load

app = FastAPI()

# Пути к основным директориям и файлам проекта
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent.parent

DATA_DIR = PROJECT_ROOT / "data" / "clean"
MODEL_DIR = PROJECT_ROOT / "models"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

CSV_PATH = DATA_DIR / "clean_deposits.csv"
MODEL_PATH = MODEL_DIR / "deposit_recommender.joblib"

# Монтируем статику и шаблоны Jinja2
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Глобальная переменная для отслеживания статуса обновления модели
progress_data = {"status": "Готов к обновлению", "progress": 0, "active": False}

# Загрузка модели и данных при старте сервера
artifact = None
pipeline = None
threshold = None
df = pd.DataFrame()

if MODEL_PATH.exists():
    artifact = load(MODEL_PATH)
    pipeline = artifact.get("pipeline")
    threshold = artifact.get("threshold", 0.2)
    print(f"[INFO] Модель загружена: {MODEL_PATH.name}")
else:
    print("[WARNING] Модель не найдена! Сначала запустите обновление.")

if CSV_PATH.exists():
    df = pd.read_csv(CSV_PATH)
    print(f"[INFO] Данные загружены: {len(df)} записей.")
else:
    print("[WARNING] CSV файл с данными не найден!")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Главная страница с формой для ввода параметров вклада.
    """
    return templates.TemplateResponse("recommend.html", {"request": request})


@app.post("/recommend", response_class=HTMLResponse)
def recommend(
    request: Request,
    amount: float = Form(...),
    term_months: int = Form(...),
    risk_tolerance: str = Form(...),
    goal: str = Form(...),
    can_replenish: str = Form("any"),
):
    """
    Обрабатывает запрос на рекомендации вкладов.
    Фильтрует данные по введённым параметрам и
    рассчитывает вероятность рекомендации с помощью модели.
    """
    if pipeline is None or df.empty:
        return templates.TemplateResponse(
            "recommend.html",
            {"request": request, "error": "Модель или данные не загружены."},
        )

    # Фильтрация по сумме и сроку вклада
    df_user = df[
        (df["min_amount"] <= amount) & (df["term_months"] <= term_months)
    ].copy()

    # Фильтрация по возможности пополнения, если задано
    if can_replenish == "yes":
        df_user = df_user[df_user["can_replenish"] == 1]
    elif can_replenish == "no":
        df_user = df_user[df_user["can_replenish"] == 0]
    # if can_replenish == "any" — фильтр не применяется

    if df_user.empty:
        return templates.TemplateResponse(
            "recommend.html",
            {"request": request, "error": "Нет вкладов под ваш запрос"},
        )

    # Обеспечиваем наличие колонки 'id' для модели
    if "id" not in df_user.columns:
        df_user = df_user.reset_index(drop=False)
        df_user.rename(columns={"index": "id"}, inplace=True)

    # Определяем признаки, которые ожидает модель (в правильном порядке)
    features = [
        "id",
        "rate",
        "term_months",
        "can_replenish",
        "min_amount",
        "currency_RUB",
        "currency_USD",
        "payout_mode_monthly",
        "risk_level",
        "goal_accumulation",
    ]

    # Проверяем, что все необходимые признаки есть в данных
    missing_cols = [col for col in features if col not in df_user.columns]
    if missing_cols:
        return templates.TemplateResponse(
            "recommend.html",
            {
                "request": request,
                "error": f"Отсутствуют признаки: {', '.join(missing_cols)}",
            },
        )

    # Отбираем только признаки, нужные модели
    df_user_filtered = df_user[features]

    # Предсказываем вероятность рекомендации
    proba = pipeline.predict_proba(df_user_filtered)[:, 1]
    df_user["probability"] = proba

    # Отбираем рекомендации с вероятностью выше порога
    recs = (
        df_user.loc[proba >= threshold]
        .sort_values("rate", ascending=False)
        .to_dict("records")
    )
    # Если рекомендаций нет, просто возвращаем топ-5 по ставке
    if not recs:
        recs = df_user.sort_values("rate", ascending=False).head(5).to_dict("records")

    return templates.TemplateResponse(
        "recommend.html",
        {
            "request": request,
            "error": None,
            "top3": recs[:3],
            "next3": recs[3:6],
            "hidden": recs[6:11],
            "threshold": threshold,
        },
    )


async def run_commands():
    """
    Фоновая задача для обновления данных и обучения модели.
    Последовательно запускает парсинг, подготовку данных и обучение.
    """
    global progress_data
    python_exec = sys.executable

    progress_data["active"] = True

    progress_data["status"] = "Парсинг страниц..."
    progress_data["progress"] = 50
    # subprocess.run([python_exec, "-m", "backend.app.parsers.pars"], check=True)

    progress_data["status"] = "Подготовка данных..."
    progress_data["progress"] = 75
    subprocess.run(
        [
            python_exec,
            "scripts/data_prep.py",
            "--db_conn",
            "postgresql://kirill:your_password@localhost:5432/deposit_db",
            "--table",
            "deposits",
            "--output",
            "data/clean/clean_deposits.csv",
        ]
    )

    progress_data["status"] = "Обучение модели..."
    progress_data["progress"] = 90
    subprocess.run([python_exec, "scripts/train_model.py"])

    progress_data["status"] = "Парсинг успешно закончен."
    progress_data["progress"] = 100
    progress_data["active"] = False


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    """
    Админ-панель отображения статуса фонового обновления модели.
    """
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "status": progress_data["status"],
            "progress": progress_data["progress"],
            "active": progress_data["active"],
        },
    )


@app.get("/admin/progress")
def get_progress():
    """
    API для получения текущего статуса и прогресса обновления.
    """
    return progress_data


@app.post("/admin/update")
def trigger_update(background_tasks: BackgroundTasks):
    """
    Запуск фоновой задачи обновления данных и модели.
    """
    background_tasks.add_task(run_commands)
    return JSONResponse({"message": "Процесс запущен!"})
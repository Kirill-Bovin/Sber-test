import subprocess
from pathlib import Path


from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from joblib import load
import pandas as pd

app = FastAPI()

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

progress_data = {"status": "Готов к обновлению", "progress": 0, "active": False}

MODEL_PATH = BASE_DIR.parent.parent / "models" / "logreg_rec.joblib"
DF_PATH = BASE_DIR.parent.parent / "data" / "clean" / "clean_deposits.csv"

artifact = None
pipeline = None
threshold = None
df = pd.DataFrame()

if MODEL_PATH.exists():
    artifact = load(MODEL_PATH)
    pipeline = artifact.get("pipeline")
    threshold = artifact.get("threshold")
    print("[INFO] Модель загружена.")
else:
    print("[WARNING] Модель не найдена! Сначала запустите обновление.")

if DF_PATH.exists():
    df = pd.read_csv(DF_PATH)
    print(f"[INFO] Данные загружены: {len(df)} записей.")
else:
    print("[WARNING] CSV файл с данными не найден!")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("recommend.html", {"request": request})

@app.post("/recommend", response_class=HTMLResponse)
def recommend(request: Request, amount: float = Form(...), term_months: int = Form(...), risk_tolerance: str = Form(...), goal: str = Form(...)):
    if pipeline is None or df.empty:
        return templates.TemplateResponse("recommend.html", {"request": request, "error": "Модель или данные не загружены."})

    df_user = df[(df["min_amount"] <= amount) & (df["term_months"] <= term_months)].copy()
    if df_user.empty:
        return templates.TemplateResponse("recommend.html", {"request": request, "error": "Нет вкладов под ваш запрос"})

    X_user = df_user[["rate", "term_months", "min_amount", "risk_level", "goal_accumulation"]]
    proba = pipeline.predict_proba(X_user)[:, 1]
    recs = df_user.loc[proba >= threshold].sort_values("rate", ascending=False).to_dict("records")
    if not recs:
        recs = df_user.sort_values("rate", ascending=False).head(5).to_dict("records")

    return templates.TemplateResponse("recommend.html", {
        "request": request,
        "error": None,
        "top3": recs[:3],
        "next3": recs[3:6],
        "hidden": recs[6:]
    })


async def run_commands():
    global progress_data
    progress_data["status"] = "Парсинг страниц..."
    progress_data["progress"] = 50
    subprocess.run(["python", "-m", "backend.app.parsers.pars"], check=True)

    progress_data["status"] = "Подготовка данных..."
    progress_data["progress"] = 75
    subprocess.run([
        "python",
        "scripts/data_prep.py",
        "--db_conn", "postgresql://kirill:your_password@localhost:5432/deposit_db",
        "--table", "deposits",
        "--output", "data/clean/clean_deposits.csv"
    ])

    progress_data["status"] = "Обучение модели..."
    progress_data["progress"] = 90
    subprocess.run(["python", "scripts/train_model.py"])

    progress_data["status"] = "Парсинг успешно закончен."
    progress_data["progress"] = 100
    progress_data["active"] = False

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"status": progress_data["status"], "progress": progress_data["progress"], "active": progress_data["active"]}
    )

@app.get("/admin/progress")
def get_progress():
    return progress_data

@app.post("/admin/update")
def trigger_update(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_commands)
    return JSONResponse({"message": "Процесс запущен!"})



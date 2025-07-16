import time
from pathlib import Path
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def save_page(url: str, basename: str, driver):
    save_dir = Path(__file__).parent.parent / "page_sber"
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / f"{basename}.html"

    def wait_rates(timeout=20):
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.dk-sbol-list"))
        )

    driver.get(url)
    # Закрываем баннер с cookies, если он есть
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "button.cookie-banner__close")
        close_btn.click()
        print("Закрыл баннер cookies")
    except NoSuchElementException:
        pass

    # Первый заход: ждем контент
    try:
        wait_rates(20)
        print(f"[{basename}] Список ставок появился при первом заходе.")
    except TimeoutException:
        print(f"[{basename}] Список ставок НЕ появился при первом заходе, перезагружаем...")

    # Перезагрузка
    driver.refresh()
    # Опять закрываем cookies (на некоторых страницах баннер может вылезть заново)
    try:
        driver.find_element(By.CSS_SELECTOR, "button.cookie-banner__close").click()
    except NoSuchElementException:
        pass

    # Второй заход: ждем контент ещё раз
    try:
        wait_rates(30)
        print(f"[{basename}] Список ставок появился после перезагрузки.")
    except TimeoutException:
        print(f"[{basename}] ОШИБКА: список ставок не найден даже после перезагрузки.")
        snippet = driver.page_source[:1000]
        print("Первых 1000 символов страницы:\n", snippet)
        raise

    # Небольшая доводящая пауза
    time.sleep(2)

    # Сохраняем финальный HTML
    with open(path, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"Сохранено: {path}")
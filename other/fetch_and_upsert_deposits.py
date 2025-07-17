#!/usr/bin/env python3
import asyncio
import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Ваша ORM-модель
from backend.app.db.models import Deposit

# --- Настройка .env ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задана в .env")


# --- Утилиты ---
def parse_term_to_months(term: str) -> int:
    months = 0
    y = re.search(r"(\d+)\s*год", term)
    if y:
        months += int(y.group(1)) * 12
    m = re.search(r"(\d+)\s*мес", term)
    if m:
        months += int(m.group(1))
    return months


async def upsert_deposits(session: AsyncSession, records: list[dict]):
    if not records:
        return
    stmt = insert(Deposit).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["name", "term_months", "payout_mode", "min_amount"],
        set_={
            "rate": stmt.excluded.rate,
            "can_replenish": stmt.excluded.can_replenish,
            "currency": stmt.excluded.currency,
            "min_amount": stmt.excluded.min_amount,
        },
    )
    await session.execute(stmt)
    await session.commit()


# --- Шаг 1: достаём cookies из Selenium ---
def get_cookies_from_selenium():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get("https://www.sberbank.com/ru/person/contributions/deposits/vklad")
        driver.implicitly_wait(5)
        return {c["name"]: c["value"] for c in driver.get_cookies()}
    finally:
        driver.quit()


# --- Шаг 2: запрос JSON через requests + cookies from Selenium ---
def fetch_json(cookies: dict, save_path: Path):
    session = requests.Session()
    session.cookies.update(cookies)
    url = "https://www.sberbank.com/proxy/services/deposit/dict/deposit/valQvbGroup/all_deposits_catalog"
    params = {"terrBankCode": "038", "timeZone": "0"}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.sberbank.com/ru/person/contributions/deposits",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0 Safari/537.36",
    }
    resp = session.get(url, params=params, headers=headers)
    print("→ JSON request URL:", resp.url)
    print("→ Status:", resp.status_code)
    resp.raise_for_status()
    save_path.parent.mkdir(exist_ok=True, parents=True)
    save_path.write_text(resp.text, encoding="utf-8")
    print("✅ JSON сохранён в", save_path)
    return resp.json()


# --- Основной async ---
async def main():
    data_dir = Path(__file__).parent / "data_sber"
    json_file = data_dir / "all_deposits_catalog.json"

    # 1) Selenium → cookies
    print("[1/3] Получаем cookies через Selenium…")
    cookies = get_cookies_from_selenium()

    # 2) requests → JSON + сохранение
    print("[2/3] Загружаем JSON с endpoint…")
    raw = fetch_json(cookies, json_file)

    # 3) Парсим и upsert в БД
    print("[3/3] Парсим и сохраняем в БД…")
    deposits = raw.get("deposits", [])
    records = []
    for d in deposits:
        records.append(
            {
                "name": d.get("name"),
                "term_months": parse_term_to_months(d.get("minTerm", "")),
                "rate": d.get("maxRate"),
                "can_replenish": bool(
                    re.search(r"пополн", d.get("description", ""), re.IGNORECASE)
                ),
                "min_amount": (
                    int(re.sub(r"\D", "", d.get("minAmount", "")))
                    if d.get("minAmount")
                    else 0
                ),
                "currency": {156: "RUB", 840: "USD", 978: "EUR"}.get(
                    d.get("catalogCurrency"), "RUB"
                ),
                "payout_mode": "end",
            }
        )
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        await upsert_deposits(session, records)
        print(f"[OK] В БД добавлено/обновлено: {len(records)} записей")


if __name__ == "__main__":
    asyncio.run(main())

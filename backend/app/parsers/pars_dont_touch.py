#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Deposit

"""Этот скрипт перезапишет таблицу в БД лучше не трогать!!!!
   Просто для ознакомления!
   Спарситься 90 записей со сбера: лучший и сбервклад"""

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задана")

ENTITY_ID = 1291
URL = (
    f"https://www.sberbank.com/proxy/services/deposit/"
    f"dict/depositCalc/valQvbGroup/{ENTITY_ID}"
)
PARAMS = {"terrBankCode": "038", "timeZone": "0"}
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.sberbank.com/ru/person/contributions/deposits",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    ),
}


async def upsert_deposits(session: AsyncSession, records: list[dict]):
    if not records:
        return
    # Построение SQL-запроса для вставки с обновлением при конфликте
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


async def main():
    # Получаем данные с сайта Сбербанка
    resp = requests.get(URL, params=PARAMS, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    # Сохраняем "сырые" данные в json для отладки или дальнейшего анализа
    out_dir = Path(__file__).parent / "data_sber"
    out_dir.mkdir(exist_ok=True)
    raw_path = out_dir / f"calc_{ENTITY_ID}.json"
    raw_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Raw JSON saved to {raw_path}")

    # Парсим и собираем нужные поля из JSON-ответа
    records_raw = []
    for block in data.get("valQvbList", []):
        currency = {643: "RUB", 810: "RUB", 840: "USD", 978: "EUR"}.get(
            block["currencyCode"], "RUB"
        )
        for cs in block.get("csQvbList", []):
            for q in cs.get("qvbList", []):
                name = q.get("depositShortName") or q["depositName"]
                term_m = q.get("begTerm", 0)
                can_repl = bool(q.get("isReplenish", False))  # ← вот здесь
                for t in q.get("dcfTarList", []):
                    records_raw.append(
                        {
                            "name": name,
                            "term_months": term_m,
                            "rate": t["rate"],
                            "can_replenish": can_repl,
                            "min_amount": t["sumBeg"],
                            "currency": currency,
                            "payout_mode": "end",
                        }
                    )

    # Оставляем уникальные записи, выбирая с максимальной ставкой
    unique = {}
    for r in records_raw:
        key = (r["name"], r["term_months"], r["payout_mode"], r["min_amount"])
        prev = unique.get(key)
        if not prev or r["rate"] > prev["rate"]:
            unique[key] = r
    records = list(unique.values())

    # Логируем распарсенные записи
    print(f"→ Parsed {len(records)} unique rows:")
    for r in records:
        print(
            f"{r['name']:<25} | term={r['term_months']:2d} мес | "
            f"min={r['min_amount']:8.2f} | rate={r['rate']:5.2f}%"
        )

    # Создаём асинхронный движок SQLAlchemy и сессию
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        await upsert_deposits(session, records)
        print(f"[OK] Upserted {len(records)} records into DB")


if __name__ == "__main__":
    asyncio.run(main())
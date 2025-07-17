from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.db.models import Deposit


async def create_or_update_deposit(
    session: AsyncSession, deposit_data: dict
) -> Deposit:
    """
    Создаёт новую запись вклада или обновляет существующую по уникальному имени.

    Параметры:
        session (AsyncSession): асинхронная сессия SQLAlchemy
        deposit_data (dict): данные вклада

    Возвращает:
        Deposit: объект вклада из базы после создания или обновления
    """
    stmt = select(Deposit).where(Deposit.name == deposit_data["name"])
    result = await session.execute(stmt)
    deposit = result.scalars().first()

    if not deposit:
        # Если вклад с таким именем отсутствует, создаём новый
        deposit = Deposit(**deposit_data)
        session.add(deposit)
        await session.commit()
        await session.refresh(deposit)
    else:
        # Если вклад найден — обновляем его поля
        for key, value in deposit_data.items():
            setattr(deposit, key, value)
        await session.commit()

    return deposit


async def create_or_update_deposit_bulk(session, deposit_data: list[dict]):
    """
    Массовая вставка или обновление записей Deposit (upsert) с помощью
    PostgreSQL оператора ON CONFLICT DO UPDATE.

    Используется составной уникальный ключ по полям:
    "name", "term_months", "payout_mode", "min_amount".

    Параметры:
        session (AsyncSession): асинхронная сессия SQLAlchemy
        deposit_data (list[dict]): список словарей с данными вкладов
    """
    if not deposit_data:
        return

    stmt = insert(Deposit).values(deposit_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["name", "term_months", "payout_mode", "min_amount"],
        set_={
            "rate": stmt.excluded.rate,
            "can_replenish": stmt.excluded.can_replenish,
            "min_amount": stmt.excluded.min_amount,
            "currency": stmt.excluded.currency,
        },
    )
    await session.execute(stmt)
    await session.commit()
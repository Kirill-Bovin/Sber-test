from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.db.models import Deposit
from sqlalchemy.dialects.postgresql import insert

async def create_or_update_deposit(session: AsyncSession, deposit_data: dict) -> Deposit:
    stmt = select(Deposit).where(Deposit.name == deposit_data["name"])
    result = await session.execute(stmt)
    deposit = result.scalars().first()

    if not deposit:
        deposit = Deposit(**deposit_data)
        session.add(deposit)
        await session.commit()
        await session.refresh(deposit)
    else:
        for key, value in deposit_data.items():
            setattr(deposit, key, value)
        await session.commit()

    return deposit

async def create_or_update_deposit_bulk(session, deposit_data: list[dict]):
    if not deposit_data:
        return

    stmt = insert(Deposit).values(deposit_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['name', 'term_months', 'payout_mode', 'min_amount'],
        set_={
            'rate': stmt.excluded.rate,
            'can_replenish': stmt.excluded.can_replenish,
            'min_amount': stmt.excluded.min_amount,
            'currency': stmt.excluded.currency,
        }
    )
    await session.execute(stmt)
    await session.commit()
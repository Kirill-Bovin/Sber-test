from sqlalchemy import Boolean, Column, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Deposit(Base):
    """
    Модель таблицы 'deposits' для хранения данных о вкладах.

    Каждая запись описывает один тип вклада с параметрами:
    - name: название вклада
    - rate: процентная ставка
    - term_months: срок вклада в месяцах
    - can_replenish: можно ли пополнять вклад
    - min_amount: минимальная сумма вклада
    - currency: валюта вклада (по умолчанию RUB)
    - payout_mode: способ выплаты процентов (по умолчанию "end" — в конце срока)
    """

    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор записи
    name = Column(String, nullable=False)  # Название вклада
    rate = Column(Float, nullable=False)  # Процентная ставка
    term_months = Column(Integer, nullable=False)  # Срок вклада в месяцах
    can_replenish = Column(Boolean, nullable=False)  # Можно ли пополнять вклад
    min_amount = Column(Float, nullable=False)  # Минимальная сумма вклада
    currency = Column(String, default="RUB", nullable=False)  # Валюта вклада
    payout_mode = Column(String, default="end", nullable=False)  # Способ выплаты процентов

    __table_args__ = (
        UniqueConstraint(
            "name",
            "term_months",
            "payout_mode",
            "min_amount",
            name="uq_name_term_payout_min",
        ),  # Составной уникальный индекс для предотвращения дублирования
    )

    def __repr__(self):
        return (
            f"<Deposit(name={self.name}, rate={self.rate}, term={self.term_months}m, "
            f"replenish={self.can_replenish}, min_amount={self.min_amount}, payout_mode={self.payout_mode})>"
        )
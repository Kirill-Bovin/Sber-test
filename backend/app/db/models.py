from sqlalchemy import Column, Integer, String, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Deposit(Base):
    __tablename__ = 'deposits'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    term_months = Column(Integer, nullable=False)
    can_replenish = Column(Boolean, nullable=False)
    min_amount = Column(Float, nullable=False)
    currency = Column(String, default='RUB', nullable=False)
    payout_mode = Column(String, default='end', nullable=False)
    __table_args__ = (
        UniqueConstraint("name", "term_months", "payout_mode", "min_amount", name="uq_name_term_payout_min"),
    )

    def __repr__(self):
        return (f"<Deposit(name={self.name}, rate={self.rate}, term={self.term_months}m, "
                f"replenish={self.can_replenish}, min_amount={self.min_amount}, payout_mode={self.payout_mode})>")
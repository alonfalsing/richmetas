from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .Base import Base


class BalanceLoad(Base):
    __tablename__ = 'balance_load'

    id = Column(Integer, primary_key=True)
    balance_id = Column(Integer, ForeignKey('balance.id'), unique=True, nullable=False)
    tx_hash = Column(String, unique=True, nullable=False)

    balance = relationship('Balance')

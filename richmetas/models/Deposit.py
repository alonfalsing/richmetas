from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from .Balance import BalanceSchema
from .Base import Base
from .BigNumber import BigNumber
from .Transaction import TransactionSchema


class Deposit(Base):
    __tablename__ = 'deposit'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transaction.id'), unique=True, nullable=False)
    balance_id = Column(Integer, ForeignKey('balance.id'), nullable=False)
    amount = Column(Numeric(precision=80), nullable=False)

    transaction = relationship('Transaction', back_populates='deposit')
    balance = relationship('Balance', back_populates='deposits')


class DepositSchema(Schema):
    transaction = fields.Nested(TransactionSchema())
    balance = fields.Nested(BalanceSchema())
    amount = BigNumber()

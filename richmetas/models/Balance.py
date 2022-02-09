from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .Base import Base
from .BigNumber import BigNumber
from .TokenContract import TokenContractSchema


class Balance(Base):
    __tablename__ = 'balance'
    __table_args__ = (
        UniqueConstraint('account_id', 'contract_id'),)

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    contract_id = Column(Integer, ForeignKey('token_contract.id'), nullable=False)
    amount = Column(Numeric(precision=80), nullable=False)

    account = relationship('Account')
    contract = relationship('TokenContract')
    deposits = relationship('Deposit', back_populates='balance')
    withdrawals = relationship('Withdrawal', back_populates='balance')


class BalanceSchema(Schema):
    contract = fields.Nested(TokenContractSchema())
    amount = BigNumber()

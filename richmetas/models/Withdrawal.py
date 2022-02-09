from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from web3 import Web3

from .Balance import BalanceSchema
from .Base import Base
from .BigNumber import BigNumber
from .Transaction import TransactionSchema


class Withdrawal(Base):
    __tablename__ = 'withdrawal'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transaction.id'), unique=True, nullable=False)
    balance_id = Column(Integer, ForeignKey('balance.id'), nullable=False)
    amount = Column(Numeric(precision=80), nullable=False)
    _address = Column(String, nullable=False)
    nonce = Column(Numeric(precision=80), nullable=False)

    @hybrid_property
    def address(self):
        return self._address

    @address.setter
    def address(self, address):
        self._address = Web3.toChecksumAddress(address)

    transaction = relationship('Transaction', back_populates='withdrawal')
    balance = relationship('Balance', back_populates='withdrawals')


class WithdrawalSchema(Schema):
    transaction = fields.Nested(TransactionSchema())
    balance = fields.Nested(BalanceSchema())
    amount = BigNumber()
    address = fields.String()
    nonce = BigNumber()

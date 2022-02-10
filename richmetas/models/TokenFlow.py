from enum import Enum

from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, Numeric, Boolean, String, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from web3 import Web3

from .Base import Base
from .BigNumber import BigNumber
from .EthEvent import EthEventSchema
from .Token import TokenSchema
from .Transaction import TransactionSchema


class FlowType(Enum):
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    TRANSFER = 'TRANSFER'
    MINT = 'MINT'


class TokenFlow(Base):
    __tablename__ = 'token_flow'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transaction.id'), unique=True, nullable=False)
    type = Column(String, nullable=False)
    token_id = Column(Integer, ForeignKey('token.id'), nullable=False)
    from_account_id = Column(Integer, ForeignKey('account.id'))
    to_account_id = Column(Integer, ForeignKey('account.id'))
    _address = Column(String)
    mint = Column(Boolean)
    nonce = Column(Numeric(precision=80))
    event_id = Column(Integer, ForeignKey('eth_event.id'), unique=True)

    @hybrid_property
    def address(self):
        return self._address

    @address.setter
    def address(self, address):
        self._address = Web3.toChecksumAddress(address)

    transaction = relationship('Transaction', back_populates='token_flow')
    token = relationship('Token', back_populates='flows')
    from_account = relationship('Account', foreign_keys=from_account_id)
    to_account = relationship('Account', foreign_keys=to_account_id)
    event = relationship('EthEvent')


class TokenFlowSchema(Schema):
    transaction = fields.Nested(TransactionSchema())
    type = fields.String()
    token = fields.Nested(TokenSchema())
    address = fields.String()
    nonce = BigNumber()
    receipt = fields.Nested(EthEventSchema(), attribute='event')

from enum import IntEnum

from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from .Account import AccountSchema
from .Base import Base
from .BigNumber import BigNumber
from .Token import TokenSchema
from .TokenContract import TokenContractSchema
from .Transaction import TransactionSchema


class Side(IntEnum):
    ASK = 0
    BID = 1


class State(IntEnum):
    NEW = 0
    FULFILLED = 1
    CANCELLED = 2


class LimitOrder(Base):
    __tablename__ = 'limit_order'

    id = Column(Integer, primary_key=True)
    order_id = Column(Numeric(precision=80), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    bid = Column(Boolean, nullable=False)
    token_id = Column(Integer, ForeignKey('token.id'), nullable=False)
    quote_contract_id = Column(Integer, ForeignKey('token_contract.id'), nullable=False)
    quote_amount = Column(Numeric(precision=80), nullable=False)
    tx_id = Column(Integer, ForeignKey('transaction.id'), nullable=False)
    closed_tx_id = Column(Integer, ForeignKey('transaction.id'))
    fulfilled = Column(Boolean)

    user = relationship('Account')
    token = relationship('Token', foreign_keys=token_id)
    quote_contract = relationship('TokenContract', foreign_keys=quote_contract_id)
    tx = relationship('Transaction', foreign_keys=tx_id)
    closed_tx = relationship('Transaction', foreign_keys=closed_tx_id)

    @property
    def state(self):
        if self.fulfilled is None:
            return State.NEW

        if self.fulfilled is True:
            return State.FULFILLED

        return State.CANCELLED


class LimitOrderCompactSchema(Schema):
    order_id = BigNumber()
    bid = fields.Boolean()
    quote_contract = fields.Nested(TokenContractSchema())
    quote_amount = BigNumber()
    state = fields.Function(lambda x: x.state.name)


class LimitOrderSchema(LimitOrderCompactSchema):
    user = fields.Nested(AccountSchema())
    token = fields.Nested(TokenSchema())
    tx = fields.Nested(TransactionSchema())
    closed_tx = fields.Nested(TransactionSchema())

from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship

from richmetas.utils import parse_int
from .Base import Base
from .Block import BlockSchema

TYPE_DEPLOY = 'DEPLOY'


class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True)
    hash = Column(String, unique=True, nullable=False)
    block_number = Column(Integer, ForeignKey('block.id'), nullable=False)
    transaction_index = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    contract_id = Column(Integer, ForeignKey('stark_contract.id'), nullable=False)
    entry_point_selector = Column(String)
    entry_point_type = Column(String)
    calldata = Column(JSON, nullable=False)

    block = relationship('Block', back_populates='transactions')
    contract = relationship('StarkContract', back_populates='transactions')
    deposit = relationship('Deposit', back_populates='transaction', uselist=False)
    withdrawal = relationship('Withdrawal', back_populates='transaction', uselist=False)
    token_flow = relationship('TokenFlow', back_populates='transaction', uselist=False)

    @property
    def params(self):
        return [*map(parse_int, self.calldata)]


class TransactionSchema(Schema):
    hash = fields.String()
    block = fields.Nested(BlockSchema())

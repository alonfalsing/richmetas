from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, String, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .Base import Base
from .EthBlock import EthBlockSchema


class EthEvent(Base):
    __tablename__ = 'eth_event'
    __table_args__ = (
        UniqueConstraint('block_number', 'log_index'),
        UniqueConstraint('hash', 'log_index'))

    id = Column(Integer, primary_key=True)
    hash = Column(String, nullable=False)
    block_number = Column(Integer, ForeignKey('eth_block.id'), nullable=False)
    log_index = Column(Integer, nullable=False)
    transaction_index = Column(Integer, nullable=True)
    body = Column(JSON, nullable=False)

    block = relationship('EthBlock', back_populates='events')


class EthEventSchema(Schema):
    hash = fields.String()
    block = fields.Nested(EthBlockSchema())

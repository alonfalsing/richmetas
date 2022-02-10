from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from .Base import Base


class EthBlock(Base):
    __tablename__ = 'eth_block'

    id = Column(Integer, primary_key=True)
    hash = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    events = relationship('EthEvent', back_populates='block')


class EthBlockSchema(Schema):
    number = fields.Integer(attribute='id')
    hash = fields.String()
    timestamp = fields.DateTime()

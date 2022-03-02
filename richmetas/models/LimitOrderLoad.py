from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .Base import Base


class LimitOrderLoad(Base):
    __tablename__ = 'limit_order_load'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('limit_order.id'))
    tx_hash = Column(String, unique=True, nullable=False)
    tx_hash2 = Column(String, unique=True)

    order = relationship('LimitOrder')

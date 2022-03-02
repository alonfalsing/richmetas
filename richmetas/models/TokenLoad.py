from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .Base import Base


class TokenLoad(Base):
    __tablename__ = 'token_load'

    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('token.id'), unique=True, nullable=False)
    tx_hash = Column(String, unique=True, nullable=False)

    token = relationship('Token')

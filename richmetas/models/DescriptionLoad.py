from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .Base import Base


class DescriptionLoad(Base):
    __tablename__ = 'description_load'

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('token_contract.id'), unique=True, nullable=False)
    tx_hash = Column(String, unique=True, nullable=False)

    contract = relationship('TokenContract')

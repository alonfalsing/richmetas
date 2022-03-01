from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .Base import Base


class LoginLoad(Base):
    __tablename__ = 'login_load'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'), unique=True, nullable=False)
    tx_hash = Column(String, unique=True, nullable=False)

    account = relationship('Account')

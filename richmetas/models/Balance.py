from sqlalchemy import Column, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from richmetas.models import Base


class Balance(Base):
    __tablename__ = 'balance'
    __table_args__ = (
        UniqueConstraint('account_id', 'contract_id'),)

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    contract_id = Column(Integer, ForeignKey('token_contract.id'), nullable=False)
    amount = Column(Numeric(precision=80), nullable=False)

    account = relationship('Account')
    contract = relationship('TokenContract')

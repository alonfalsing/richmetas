from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship

from richmetas.models import Base


class Transfer(Base):
    __tablename__ = 'transfer'

    id = Column(Integer, primary_key=True)
    from_account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    to_account_id = Column(Integer, ForeignKey('account.id'), nullable=False)
    amount = Column(Numeric(precision=80), nullable=False)
    contract_id = Column(Integer, ForeignKey('token_contract.id'), nullable=False)
    nonce = Column(Numeric(precision=80), nullable=False)
    signature_r = Column(Numeric(precision=80))
    signature_s = Column(Numeric(precision=80))
    hash = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=True)

    from_account = relationship('Account', foreign_keys=from_account_id)
    to_account = relationship('Account', foreign_keys=to_account_id)
    contract = relationship('TokenContract')

from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from web3 import Web3

from .Base import Base
from .BigNumber import BigNumber


class Account(Base):
    __tablename__ = 'account'

    id = Column(Integer, primary_key=True)
    stark_key = Column(Numeric(precision=80), nullable=False)
    _address = Column('address', String, unique=True)

    tokens = relationship('Token', back_populates='owner')

    @hybrid_property
    def address(self):
        return self._address

    @address.setter
    def address(self, address):
        self._address = Web3.toChecksumAddress(address)

    def __eq__(self, other):
        return isinstance(other, Account) and self.stark_key == other.stark_key


class AccountSchema(Schema):
    stark_key = BigNumber()
    address = fields.String()

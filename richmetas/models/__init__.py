from marshmallow import fields

from .Base import Base
from .Block import Block
from .StarkContract import StarkContract
from .Transaction import Transaction

from .Account import Account
from .Balance import Balance
from .Blueprint import Blueprint, BlueprintSchema
from .Deposit import Deposit, DepositSchema
from .LimitOrder import LimitOrder, LimitOrderSchema, State
from .Token import Token, TokenSchema
from .TokenContract import TokenContract, TokenContractSchema
from .TokenFlow import TokenFlow, TokenFlowSchema, FlowType
from .Transfer import Transfer
from .Withdrawal import Withdrawal, WithdrawalSchema


class TokenContractVerboseSchema(TokenContractSchema):
    blueprint = fields.Nested(BlueprintSchema())


class TokenVerboseSchema(TokenSchema):
    from .Account import AccountSchema
    from .LimitOrder import LimitOrderCompactSchema

    owner = fields.Nested(AccountSchema())
    ask = fields.Nested(LimitOrderCompactSchema())

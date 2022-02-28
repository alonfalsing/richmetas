from collections import namedtuple

from marshmallow import Schema, fields

from richmetas import utils
from richmetas.contracts.starknet.base import Base, BaseFeeder
from richmetas.models import State
from richmetas.sign import authenticate_rr

LimitOrder = namedtuple('LimitOrder', [
    'user',
    'bid',
    'base_contract',
    'base_token_id',
    'quote_contract',
    'quote_amount',
    'state',
])
LimitOrderSchema = Schema.from_dict({
    'user': fields.String(),
    'bid': fields.Boolean(),
    'base_contract': fields.Function(lambda x: utils.to_checksum_address(x.base_contract)),
    'base_token_id': fields.String(),
    'quote_contract': fields.Function(lambda x: utils.to_checksum_address(x.quote_contract)),
    'quote_amount': fields.String(),
    'state': fields.Function(lambda x: State(x.state).name),
})


class Exchange(BaseFeeder):
    async def get_order(self, id_):
        result = await self._call('get_order', [id_])

        return LimitOrder._make(result)


class ExchangeFacade(Base):
    def create_order(self, id_, limit_order: LimitOrder, signature):
        authenticate_rr(limit_order.user, id_, *limit_order[1:-1], signature=signature)

        return self._invoke('create_order', [id_, *limit_order[:-1]], signature)

    def fulfill_order(self, id_, user, nonce, signature):
        authenticate_rr(user, id_, nonce, signature=signature)

        return self._invoke('fulfill_order', [id_, user, nonce], signature)

    def cancel_order(self, id_, nonce, signature, user=None):
        if user:
            authenticate_rr(user, id_, nonce, signature=signature)

        return self._invoke('cancel_order', [id_, nonce], signature)

from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.transaction import InvokeFunction

from richmetas.utils import parse_int


class Base:
    def __init__(self, address: int):
        self._address = address

    def invoke(self, name, calldata, signature) -> InvokeFunction:
        return InvokeFunction(
            contract_address=self._address,
            entry_point_selector=get_selector_from_name(name),
            calldata=[parse_int(x) for x in calldata],
            signature=signature)


class BaseFeeder(Base):
    def __init__(self, address: int, feeder: FeederGatewayClient):
        super().__init__(address)
        self._feeder = feeder

    async def call(self, name, calldata):
        response = await self._feeder.call_contract(self.invoke(name, calldata, []))

        return [parse_int(x) for x in response['result']]

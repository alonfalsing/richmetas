from richmetas.contracts.starknet.base import Base, BaseFeeder
from richmetas.sign import StarkKeyPair


class Login(BaseFeeder):
    async def get_account(self, ethereum_address):
        stark_key, = await self.call('get_account', [ethereum_address])

        return stark_key


class LoginFacadeAdmin(Base):
    def __init__(self, address, facade_address, key: StarkKeyPair):
        super(LoginFacadeAdmin, self).__init__(address)

        self._facade_address = facade_address
        self._key = key

    def register_account(self, stark_key, ethereum_address, nonce):
        calldata = [self._facade_address, stark_key, ethereum_address, nonce]
        signature = self._key.sign(*calldata)

        return self.invoke('register_account', calldata, [*signature])

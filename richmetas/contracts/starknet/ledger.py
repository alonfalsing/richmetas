from starkware.starknet.services.api.gateway.transaction import InvokeFunction

from richmetas.contracts.starknet.base import Base, BaseFeeder
from richmetas.sign import authenticate_rr


class Ledger(BaseFeeder):
    async def describe(self, contract):
        return await self.call('describe', [contract])

    async def get_balance(self, user, contract):
        balance, = await self.call('get_balance', [user, contract])

        return balance

    async def get_owner(self, token_id, contract):
        owner, = await self.call('get_owner', [token_id, contract])

        return owner

    async def is_mint(self, token_id, contract):
        mint, = await self.call('is_mint', [token_id, contract])

        return bool(mint)


class LedgerFacade(Base):
    def withdraw(self, user, amount_or_token_id, contract, address, nonce, signature) -> InvokeFunction:
        authenticate_rr(user, amount_or_token_id, contract, address, nonce, signature=signature)

        return self.invoke('withdraw', [user, amount_or_token_id, contract, address, nonce], signature)

    def transfer(self, from_, to_, amount_or_token_id, contract, nonce, signature) -> InvokeFunction:
        authenticate_rr(from_, to_, amount_or_token_id, contract, nonce, signature=signature)

        return self.invoke('transfer', [from_, to_, amount_or_token_id, contract, nonce], signature)

    def mint(self, user, token_id, contract, nonce, signature, minter=None) -> InvokeFunction:
        if minter:
            authenticate_rr(minter, user, token_id, contract, nonce, signature=signature)

        return self.invoke('mint', [user, token_id, contract, nonce], signature)

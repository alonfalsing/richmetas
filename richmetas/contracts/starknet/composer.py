from collections import namedtuple
from enum import IntEnum

from marshmallow import Schema, fields
from more_itertools import collapse

from richmetas import utils
from richmetas.contracts.starknet.base import Base, BaseFeeder
from richmetas.models.BigNumber import BigNumber
from richmetas.sign import authenticate


class Arm(IntEnum):
    INPUT = 1
    OUTPUT = 2
    INSTALL = 3


class State(IntEnum):
    NEW = 0
    OPEN = 1
    READY = 2
    CLOSED = 3


Stereotype = namedtuple('Stereotype', [
    'inputs',
    'outputs',
    'installs',
    'admin',
    'user',
    'state',
])
StereotypeSchema = Schema.from_dict({
    'inputs': fields.Integer(),
    'outputs': fields.Integer(),
    'installs': fields.Integer(),
    'admin': BigNumber(),
    'user': BigNumber(),
    'state': fields.Function(lambda s: State(s.state).name),
})
Token = namedtuple('Token', ['token_id', 'contract'])
TokenSchema = Schema.from_dict({
    'token_id': BigNumber(),
    'contract': fields.Function(lambda t: utils.to_checksum_address(t.contract)),
})
Install = namedtuple('Install', ['stereotype_id', 'owner'])
InstallSchema = Schema.from_dict({
    'stereotype_id': BigNumber(),
    'owner': BigNumber(),
})


class Composer(BaseFeeder):
    async def get_stereotype(self, stereotype_id):
        result = await self.call('get_stereotype', [stereotype_id])
        stereotype = Stereotype._make(result)

        return stereotype if stereotype.admin != 0 else None

    async def get_token(self, stereotype_id, arm, i):
        result = await self.call('get_token', [stereotype_id, arm, i])

        return Token._make(result)

    async def get_install(self, token_id, contract):
        result = await self.call('get_install', [token_id, contract])
        install = Install._make(result)

        return install if install.stereotype_id != 0 else None


class ComposerFacade(Base):
    def create_stereotype(self, stereotype_id, admin, user):
        return self.invoke('create_stereotype', [stereotype_id, admin, user], [])

    def add_token(self, token_id, contract, io, stereotype_id, nonce, signature):
        return self.invoke('add_token', [token_id, contract, io, stereotype_id, nonce], signature)

    def remove_token(self, token_id, contract, stereotype_id, nonce, signature):
        return self.invoke('remove_token', [token_id, contract, stereotype_id, nonce], signature)

    def activate_stereotype(self, stereotype_id, nonce, signature):
        return self.invoke('activate_stereotype', [stereotype_id, nonce], signature)

    def install_token(self, user, token_id, contract, stereotype_id, nonce, signature):
        authenticate(user, token_id, contract, stereotype_id, nonce, signature=signature, raise_exception=True)

        return self.invoke('install_token', [user, token_id, contract, stereotype_id, nonce], signature)

    def uninstall_token(self, token_id, contract, stereotype_id, nonce, signature):
        return self.invoke('uninstall_token', [token_id, contract, stereotype_id, nonce], signature)

    def execute_stereotype(self, stereotype_id, nonce, signature):
        return self.invoke('execute_stereotype', [stereotype_id, nonce], signature)

    def launch_stereotype(self, stereotype_id, admin, user, inputs, outputs, signature):
        authenticate(
            admin,
            stereotype_id,
            user,
            *collapse(inputs),
            *collapse(outputs),
            signature=signature,
            raise_exception=True)

        return self.invoke(
            'launch_stereotype',
            [stereotype_id, admin, user,
             len(inputs), *collapse(inputs),
             len(outputs), *collapse(outputs)],
            signature)

    def solve_stereotype(self, stereotype_id, nonce, signature):
        return self.invoke('solve_stereotype', [stereotype_id, nonce], signature)

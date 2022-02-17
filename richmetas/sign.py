import functools
from typing import Optional, Callable

from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash
from starkware.crypto.signature.signature import get_random_private_key, private_to_stark_key, sign


def hash_message(*args: int) -> int:
    return functools.reduce(pedersen_hash, [*args, len(args)], 0)


def hash_message_r(*args: int) -> int:
    if len(args) > 1:
        return pedersen_hash(args[0], hash_message_r(*args[1:]))

    return pedersen_hash(args[0], 0)


class StarkKeyPair:
    def __init__(self, private_key: Optional[int] = None):
        self._private_key = private_key or get_random_private_key()

    @property
    def private_key(self) -> int:
        return self._private_key

    @property
    def stark_key(self):
        return private_to_stark_key(self._private_key)

    def sign(self, *args: int, hash_algo: Callable[..., int] = hash_message):
        return sign(hash_algo(*args), self._private_key)

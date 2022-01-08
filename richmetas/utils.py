from enum import Enum
from typing import Union

from eth_typing import ChecksumAddress
from web3 import Web3


def parse_int(n: Union[int, str]):
    return int(n) if isinstance(n, int) else int(n, 0)


def to_checksum_address(address) -> ChecksumAddress:
    return Web3.toChecksumAddress('%040x' % parse_int(address))


ZERO_ADDRESS = to_checksum_address(0)


class Status(Enum):
    NOT_RECEIVED = 'NOT_RECEIVED'
    RECEIVED = 'RECEIVED'
    PENDING = 'PENDING'
    REJECTED = 'REJECTED'
    ACCEPTED_ON_L2 = 'ACCEPTED_ON_L2'
    ACCEPTED_ON_L1 = 'ACCEPTED_ON_L1'
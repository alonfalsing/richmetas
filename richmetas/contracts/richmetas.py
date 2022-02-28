from enum import IntEnum

import pkg_resources
from eth_typing import ChecksumAddress, HexStr
from web3 import Web3


class ContractKind(IntEnum):
    ERC20 = 1
    ERC721 = 2


class EtherRichmetas:
    def __init__(self, stark_address: int, w3: Web3):
        self._stark_address = stark_address
        self._contract = w3.eth.contract(
            abi=pkg_resources.resource_string(__name__, 'abi/Richmetas.abi').decode())

    def register_contract(
            self,
            contract: ChecksumAddress,
            kind: ContractKind,
            minter: int) -> tuple[HexStr, int]:
        return self._contract.encodeABI('registerContract', [
            self._stark_address,
            contract,
            kind,
            minter,
        ]), 100000

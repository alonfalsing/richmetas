import os

from starkware.starknet.testing.contract import StarknetContract, StarknetContractFunctionInvocation
from starkware.starknet.testing.starknet import Starknet


async def deploy(starknet: Starknet, name: str, *constructor_calldata):
    return await starknet.deploy(
        source=os.path.join(os.path.dirname(__file__), f'{name}.cairo'),
        cairo_path=[os.path.dirname(__file__)],
        constructor_calldata=[*constructor_calldata],
    )


def proxy(f: StarknetContractFunctionInvocation, proxy_contract: StarknetContract):
    f.state = proxy_contract.state
    f.contract_address = proxy_contract.contract_address

    return f


def patch_starknet():
    Starknet.deploy_source = deploy
    StarknetContractFunctionInvocation.proxy = proxy

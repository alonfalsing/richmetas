import os

from starkware.starknet.testing.starknet import Starknet


async def deploy(starknet: Starknet, name: str, *constructor_calldata):
    return await starknet.deploy(
        source=os.path.join(os.path.dirname(__file__), f'{name}.cairo'),
        cairo_path=[os.path.dirname(__file__)],
        constructor_calldata=[*constructor_calldata],
    )


def patch_starknet():
    Starknet.deploy_source = deploy

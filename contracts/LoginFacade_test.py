from uuid import uuid4

import pytest
from eth_account import Account
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException

from contracts.util import patch_starknet
from richmetas.sign import StarkKeyPair, hash_message_r

patch_starknet()


@pytest.mark.asyncio
async def test_register_account():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    a = int(Account.create().address, 0)
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    login_contract = await starknet.deploy_source('Login', access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('LoginFacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'LoginFacade', login_contract.contract_address, facade_admin_contract.contract_address)

    calldata = [facade_contract.contract_address, k2.stark_key, a, uuid4().int]
    signature = k.sign(*calldata)
    with pytest.raises(StarkException):
        await login_contract.register_account(*calldata[1:-1]).invoke()
    with pytest.raises(StarkException):
        await facade_contract.register_account(*calldata[1:-1]).invoke()
    with pytest.raises(StarkException):
        await facade_admin_contract.register_account(*calldata).invoke(signature=[*signature])

    ac_calldata = [login_contract.contract_address, facade_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    await facade_admin_contract.register_account(*calldata).invoke(signature=[*signature])
    exec_info = await login_contract.get_account(a).call()
    assert exec_info.result == (k2.stark_key,)

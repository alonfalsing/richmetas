import pytest
from starkware.starknet.testing.starknet import Starknet

from richmetas.sign import StarkKeyPair
from util import patch_starknet

L1_CONTRACT_ADDRESS = 0x13095e61fC38a06041f2502FcC85ccF4100FDeFf
patch_starknet()


@pytest.mark.asyncio
async def test_change_owner():
    k, sk = StarkKeyPair(), StarkKeyPair().stark_key
    starknet = await Starknet.empty()
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    await facade_admin_contract. \
        change_owner(sk). \
        invoke(signature=[*k.sign(sk)])
    exec_info = await facade_admin_contract.owner().call()
    assert exec_info.result == (sk,)


@pytest.mark.asyncio
async def test_facade_underpin():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    ledger_contract2 = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'LedgerFacade', ledger_contract.contract_address, facade_admin_contract.contract_address)
    await facade_admin_contract. \
        facade_underpin(facade_contract.contract_address, ledger_contract2.contract_address). \
        invoke(signature=[*k.sign(facade_contract.contract_address, ledger_contract2.contract_address)])
    exec_info = await facade_contract.get_underpinning().call()
    assert exec_info.result == (ledger_contract2.contract_address,)

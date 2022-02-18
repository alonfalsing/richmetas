from uuid import uuid4

import pytest
from eth_account import Account
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.testing.starknet import Starknet

from contracts.util import patch_starknet
from richmetas.sign import StarkKeyPair, hash_message_r

L1_CONTRACT_ADDRESS = 0x13095e61fC38a06041f2502FcC85ccF4100FDeFf
patch_starknet()


@pytest.mark.asyncio
async def test_change_proxy_admin():
    k, sk = StarkKeyPair(), StarkKeyPair().stark_key
    starknet = await Starknet.empty()
    proxy_admin_contract = await starknet.deploy_source('ProxyAdmin', k.stark_key)
    proxy_contract = await starknet.deploy_source(
        'Proxy', 0, proxy_admin_contract.contract_address)
    await proxy_admin_contract. \
        changeProxyAdmin(proxy_contract.contract_address, sk). \
        invoke(signature=[*k.sign(proxy_contract.contract_address, sk)])
    exec_info = await proxy_contract.getAdmin().call()
    assert exec_info.result == (sk,)


@pytest.mark.asyncio
async def test_upgrade():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    proxy_admin_contract = await starknet.deploy_source('ProxyAdmin', k.stark_key)
    proxy_contract = await starknet.deploy_source(
        'Proxy', 0, proxy_admin_contract.contract_address)
    await proxy_admin_contract. \
        upgrade(proxy_contract.contract_address, ledger_contract.contract_address). \
        invoke(signature=[*k.sign(proxy_contract.contract_address, ledger_contract.contract_address)])
    exec_info = await proxy_contract.getImplementation().call()
    assert exec_info.result == (ledger_contract.contract_address,)


@pytest.mark.asyncio
async def test_l1_handler():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    proxy_admin_contract = await starknet.deploy_source('ProxyAdmin', k.stark_key)
    proxy_contract = await starknet.deploy_source(
        'Proxy', ledger_contract.contract_address, proxy_admin_contract.contract_address)
    await ledger_contract.initialize(L1_CONTRACT_ADDRESS).proxy(proxy_contract).invoke()
    await ledger_contract.change_admin(access_control_contract.contract_address).proxy(proxy_contract).invoke()

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        proxy_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).proxy(proxy_contract).call()
    assert exec_info.result == (5050,)
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).call()
    assert exec_info.result == (0,)


@pytest.mark.asyncio
async def test_external():
    k = StarkKeyPair()
    a = int(Account.create().address, 0)
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    proxy_admin_contract = await starknet.deploy_source('ProxyAdmin', k.stark_key)
    proxy_contract = await starknet.deploy_source(
        'Proxy', ledger_contract.contract_address, proxy_admin_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'LedgerFacade', proxy_contract.contract_address, facade_admin_contract.contract_address)
    await ledger_contract.initialize(L1_CONTRACT_ADDRESS).proxy(proxy_contract).invoke()
    await ledger_contract.change_admin(access_control_contract.contract_address).proxy(proxy_contract).invoke()
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        proxy_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])

    calldata = [k.stark_key, 5050, 0, a, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    await access_control_contract. \
        acl_toggle_access(proxy_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(proxy_contract.contract_address, facade_contract.contract_address, 1)])
    await facade_contract.withdraw(*calldata).invoke(signature=[*signature])
    starknet.consume_message_from_l2(
        proxy_contract.contract_address,
        L1_CONTRACT_ADDRESS,
        [0, a, calldata[1], 0, 0, calldata[4]])
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).proxy(proxy_contract).call()
    assert exec_info.result == (0,)

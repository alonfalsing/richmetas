from uuid import uuid4

import pytest
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException

from contracts.util import patch_starknet
from richmetas.sign import StarkKeyPair, hash_message_r

L1_CONTRACT_ADDRESS = 0x13095e61fC38a06041f2502FcC85ccF4100FDeFf
ERC20_CONTRACT_ADDRESS = 0x4A26C7daCcC90434693de4b8bede3151884cab89
ERC721_CONTRACT_ADDRESS = 0xfAfC4Ec8ca3Eb374fbde6e9851134816Aada912a
patch_starknet()


@pytest.mark.asyncio
async def test_create():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    exchange_contract = await starknet.deploy_source(
        'Exchange', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'ExchangeFacade', exchange_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])

    calldata = [uuid4().int, k.stark_key, 1, ERC721_CONTRACT_ADDRESS, uuid4().int, 0, 5000]
    signature = k.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await exchange_contract.create_order(*calldata).invoke(signature=[*signature])
    with pytest.raises(StarkException):
        await facade_contract.create_order(*calldata).invoke(signature=[*signature])

    await access_control_contract. \
        acl_toggle_access(ledger_contract.contract_address, exchange_contract.contract_address, 1). \
        invoke(signature=[*k.sign(ledger_contract.contract_address, exchange_contract.contract_address, 1)])
    await access_control_contract. \
        acl_toggle_access(exchange_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(exchange_contract.contract_address, facade_contract.contract_address, 1)])
    await facade_contract.create_order(*calldata).invoke(signature=[*signature])
    exec_info = await exchange_contract.get_order(calldata[0]).call()
    assert exec_info.result == (tuple([*calldata[1:], 0]),)
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).call()
    assert exec_info.result == ((50),)


@pytest.mark.asyncio
async def test_fulfill():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    exchange_contract = await starknet.deploy_source(
        'Exchange', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'ExchangeFacade', exchange_contract.contract_address, facade_admin_contract.contract_address)

    calldata = [uuid4().int, k2.stark_key, 0, ERC721_CONTRACT_ADDRESS, uuid4().int, 0, 5000]
    signature = k2.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    await access_control_contract. \
        acl_toggle_access(ledger_contract.contract_address, exchange_contract.contract_address, 1). \
        invoke(signature=[*k.sign(ledger_contract.contract_address, exchange_contract.contract_address, 1)])
    await access_control_contract. \
        acl_toggle_access(exchange_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(exchange_contract.contract_address, facade_contract.contract_address, 1)])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k2.stark_key, calldata[4], ERC721_CONTRACT_ADDRESS, uuid4().int])
    await facade_contract.create_order(*calldata).invoke(signature=[*signature])

    nonce = uuid4().int
    await facade_contract. \
        fulfill_order(calldata[0], k.stark_key, nonce). \
        invoke(signature=[*k.sign(calldata[0], nonce, hash_algo=hash_message_r)])
    exec_info = await exchange_contract.get_order(calldata[0]).call()
    assert exec_info.result == (tuple([*calldata[1:], 1]),)
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).call()
    assert exec_info.result == ((50),)
    exec_info = await ledger_contract.get_owner(calldata[4], ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == ((k.stark_key),)
    exec_info = await ledger_contract.get_balance(k2.stark_key, 0).call()
    assert exec_info.result == ((5000),)


@pytest.mark.asyncio
async def test_cancel():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    exchange_contract = await starknet.deploy_source(
        'Exchange', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'ExchangeFacade', exchange_contract.contract_address, facade_admin_contract.contract_address)

    calldata = [uuid4().int, k.stark_key, 0, ERC721_CONTRACT_ADDRESS, uuid4().int, 0, 5000]
    signature = k.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    await access_control_contract. \
        acl_toggle_access(ledger_contract.contract_address, exchange_contract.contract_address, 1). \
        invoke(signature=[*k.sign(ledger_contract.contract_address, exchange_contract.contract_address, 1)])
    await access_control_contract. \
        acl_toggle_access(exchange_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(exchange_contract.contract_address, facade_contract.contract_address, 1)])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, calldata[4], ERC721_CONTRACT_ADDRESS, uuid4().int])
    await facade_contract.create_order(*calldata).invoke(signature=[*signature])
    exec_info = await ledger_contract.get_owner(calldata[4], ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == ((exchange_contract.contract_address),)

    nonce = uuid4().int
    await facade_contract. \
        cancel_order(calldata[0], nonce). \
        invoke(signature=[*k.sign(calldata[0], nonce, hash_algo=hash_message_r)])
    exec_info = await exchange_contract.get_order(calldata[0]).call()
    assert exec_info.result == (tuple([*calldata[1:], 2]),)
    exec_info = await ledger_contract.get_owner(calldata[4], ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == ((k.stark_key),)

from uuid import uuid4

import pytest
from eth_account import Account
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException

from richmetas.sign import StarkKeyPair, hash_message_r
from util import patch_starknet

L1_CONTRACT_ADDRESS = 0x13095e61fC38a06041f2502FcC85ccF4100FDeFf
ERC20_CONTRACT_ADDRESS = 0x4A26C7daCcC90434693de4b8bede3151884cab89
ERC721_CONTRACT_ADDRESS = 0xfAfC4Ec8ca3Eb374fbde6e9851134816Aada912a
patch_starknet()


@pytest.mark.asyncio
async def test_withdraw():
    k = StarkKeyPair()
    a = int(Account.create().address, 0)
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'LedgerFacade', ledger_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])

    calldata = [k.stark_key, 5050, 0, a, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await ledger_contract.withdraw(*calldata).invoke(signature=[*signature])
    with pytest.raises(StarkException):
        await facade_contract.withdraw(*calldata).invoke(signature=[*signature])

    await access_control_contract. \
        acl_toggle_access(ledger_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(ledger_contract.contract_address, facade_contract.contract_address, 1)])
    await facade_contract.withdraw(*calldata).invoke(signature=[*signature])
    starknet.consume_message_from_l2(
        ledger_contract.contract_address,
        L1_CONTRACT_ADDRESS,
        [0, a, calldata[1], 0, 0, calldata[4]])
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).call()
    assert exec_info.result == (0,)

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, 0])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 23130, ERC20_CONTRACT_ADDRESS, uuid4().int])
    calldata = [k.stark_key, 5050, ERC20_CONTRACT_ADDRESS, a, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    await facade_contract.withdraw(*calldata).invoke(signature=[*signature])
    starknet.consume_message_from_l2(
        ledger_contract.contract_address,
        L1_CONTRACT_ADDRESS,
        [0, a, calldata[1], ERC20_CONTRACT_ADDRESS, 0, calldata[4]])
    exec_info = await ledger_contract.get_balance(k.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (18080,)
    calldata = [k.stark_key, 23130, ERC20_CONTRACT_ADDRESS, a, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await facade_contract.withdraw(*calldata).invoke(signature=[*signature])

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 21930, ERC721_CONTRACT_ADDRESS, uuid4().int])
    calldata = [k.stark_key, 21930, ERC721_CONTRACT_ADDRESS, a, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    await facade_contract.withdraw(*calldata).invoke(signature=[*signature])
    starknet.consume_message_from_l2(
        ledger_contract.contract_address,
        L1_CONTRACT_ADDRESS,
        [0, a, calldata[1], ERC721_CONTRACT_ADDRESS, 0, calldata[4]])
    exec_info = await ledger_contract.get_owner(21930, ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (0,)
    calldata = [k.stark_key, 5050, ERC721_CONTRACT_ADDRESS, a, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await facade_contract.withdraw(*calldata).invoke(signature=[*signature])


@pytest.mark.asyncio
async def test_transfer():
    k, sk = StarkKeyPair(), StarkKeyPair().stark_key
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'LedgerFacade', ledger_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])

    calldata = [k.stark_key, sk, 5050, 0, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await ledger_contract.transfer(*calldata[:-1]).invoke()
    with pytest.raises(StarkException):
        await facade_contract.transfer(*calldata).invoke(signature=[*signature])

    await access_control_contract. \
        acl_toggle_access(ledger_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(ledger_contract.contract_address, facade_contract.contract_address, 1)])
    await facade_contract.transfer(*calldata).invoke(signature=[*signature])
    exec_info = await ledger_contract.get_balance(sk, 0).call()
    assert exec_info.result == (5050,)
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).call()
    assert exec_info.result == (0,)

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, 0])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 23130, ERC20_CONTRACT_ADDRESS, uuid4().int])
    calldata = [k.stark_key, sk, 5050, ERC20_CONTRACT_ADDRESS, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    await facade_contract.transfer(*calldata).invoke(signature=[*signature])
    exec_info = await ledger_contract.get_balance(sk, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (5050,)
    exec_info = await ledger_contract.get_balance(k.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (18080,)
    calldata = [k.stark_key, sk, 23130, ERC20_CONTRACT_ADDRESS, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await facade_contract.transfer(*calldata).invoke(signature=[*signature])

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 21930, ERC721_CONTRACT_ADDRESS, uuid4().int])
    calldata = [k.stark_key, sk, 21930, ERC721_CONTRACT_ADDRESS, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    await facade_contract.transfer(*calldata).invoke(signature=[*signature])
    exec_info = await ledger_contract.get_owner(21930, ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (sk,)
    calldata = [k.stark_key, sk, 5050, ERC721_CONTRACT_ADDRESS, uuid4().int]
    signature = k.sign(*calldata[1:], hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await facade_contract.transfer(*calldata).invoke(signature=[*signature])


@pytest.mark.asyncio
async def test_mint():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    a = int(Account.create().address, 0)
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'LedgerFacade', ledger_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])

    calldata = [k2.stark_key, uuid4().int, ERC721_CONTRACT_ADDRESS, uuid4().int]
    signature = k.sign(*calldata, hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await ledger_contract.mint(*calldata[:-1]).invoke()

    with pytest.raises(StarkException):
        await facade_contract.mint(*calldata).invoke(signature=[*signature])

    await access_control_contract. \
        acl_toggle_access(ledger_contract.contract_address, facade_contract.contract_address, 1). \
        invoke(signature=[*k.sign(ledger_contract.contract_address, facade_contract.contract_address, 1)])
    await facade_contract.mint(*calldata).invoke(signature=[*signature])
    exec_info = await ledger_contract.get_owner(calldata[1], ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (k2.stark_key,)
    exec_info = await ledger_contract.is_mint(calldata[1], ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (1,)

    calldata = [k2.stark_key, calldata[1], ERC721_CONTRACT_ADDRESS, a, uuid4().int]
    signature = k2.sign(*calldata[1:], hash_algo=hash_message_r)
    await facade_contract.withdraw(*calldata).invoke(signature=[*signature])
    starknet.consume_message_from_l2(
        ledger_contract.contract_address,
        L1_CONTRACT_ADDRESS,
        [0, a, calldata[1], ERC721_CONTRACT_ADDRESS, 1, calldata[4]])

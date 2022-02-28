from time import time
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
async def test_set_revenue():
    k, sk = StarkKeyPair(), StarkKeyPair().stark_key
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    staking_contract = await starknet.deploy_source(
        'Staking', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('StakingFacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'StakingFacade', staking_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])

    calldata = [facade_contract.contract_address, ERC721_CONTRACT_ADDRESS, 5050, ERC20_CONTRACT_ADDRESS, sk, uuid4().int]
    signature = k.sign(*calldata, hash_algo=hash_message_r)
    with pytest.raises(StarkException):
        await staking_contract.set_revenue(*calldata[1:-1]).invoke()
    with pytest.raises(StarkException):
        await facade_contract.set_revenue(*calldata[1:-1]).invoke()
    with pytest.raises(StarkException):
        await facade_admin_contract.set_revenue(*calldata).invoke(signature=[*signature])

    ac_calldata = [staking_contract.contract_address, facade_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    with pytest.raises(StarkException):
        await facade_contract.set_revenue(*calldata[1:-1]).invoke()
    await facade_admin_contract.set_revenue(*calldata).invoke(signature=[*signature])
    exec_info = await staking_contract.get_revenue(ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == ((5050, ERC20_CONTRACT_ADDRESS, sk),)


@pytest.mark.asyncio
async def test_stake_non_fungible():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    staking_contract = await starknet.deploy_source(
        'Staking', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('StakingFacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'StakingFacade', staking_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    token_id = uuid4().int
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k2.stark_key, token_id, ERC721_CONTRACT_ADDRESS, uuid4().int])

    calldata = [facade_contract.contract_address, ERC721_CONTRACT_ADDRESS, 5050, ERC20_CONTRACT_ADDRESS, k.stark_key, uuid4().int]
    signature = k.sign(*calldata, hash_algo=hash_message_r)
    ac_calldata = [staking_contract.contract_address, facade_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    await facade_admin_contract.set_revenue(*calldata).invoke(signature=[*signature])
    calldata = [uuid4().int, k2.stark_key, token_id, ERC721_CONTRACT_ADDRESS]
    signature = k2.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    ac_calldata = [ledger_contract.contract_address, staking_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])

    started_at = int(time())
    starknet.set_timestamp(started_at)
    await facade_contract.stake(*calldata).invoke(signature=[*signature])
    exec_info = await ledger_contract.get_owner(token_id, ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (staking_contract.contract_address,)
    exec_info = await staking_contract.get_staking(calldata[0]).call()
    assert exec_info.result == ((k2.stark_key, token_id, ERC721_CONTRACT_ADDRESS, started_at, 0),)


@pytest.mark.asyncio
async def test_unstake_fungible():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    staking_contract = await starknet.deploy_source(
        'Staking', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('StakingFacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'StakingFacade', staking_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 1000000, ERC20_CONTRACT_ADDRESS, uuid4().int])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k2.stark_key, 1000000, 0, uuid4().int])

    calldata = [facade_contract.contract_address, 0, 200, ERC20_CONTRACT_ADDRESS, k.stark_key, uuid4().int]
    signature = k.sign(*calldata, hash_algo=hash_message_r)
    ac_calldata = [staking_contract.contract_address, facade_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    await facade_admin_contract.set_revenue(*calldata).invoke(signature=[*signature])
    calldata = [uuid4().int, k2.stark_key, 500000, 0]
    signature = k2.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    ac_calldata = [ledger_contract.contract_address, staking_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    started_at = int(time())
    starknet.set_timestamp(started_at)
    await facade_contract.stake(*calldata).invoke(signature=[*signature])

    ended_at = started_at + 2419229
    starknet.set_timestamp(ended_at)
    calldata = [calldata[0], uuid4().int]
    signature = k2.sign(*calldata, hash_algo=hash_message_r)
    await facade_contract.unstake(*calldata).invoke(signature=[*signature])
    exec_info = await staking_contract.get_staking(calldata[0]).call()
    assert exec_info.result == ((k2.stark_key, 500000, 0, started_at, ended_at),)
    exec_info = await ledger_contract.get_balance(k2.stark_key, 0).call()
    assert exec_info.result == (1000000,)
    exec_info = await ledger_contract.get_balance(k2.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (2800,)
    exec_info = await ledger_contract.get_balance(k.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (997200,)


@pytest.mark.asyncio
async def test_unstake_fungible_compound():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    staking_contract = await starknet.deploy_source(
        'Staking', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('StakingFacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'StakingFacade', staking_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 1000000, ERC20_CONTRACT_ADDRESS, uuid4().int])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k2.stark_key, 1000000, ERC20_CONTRACT_ADDRESS, uuid4().int])

    calldata = [facade_contract.contract_address, ERC20_CONTRACT_ADDRESS, 200, ERC20_CONTRACT_ADDRESS, k.stark_key, uuid4().int]
    signature = k.sign(*calldata, hash_algo=hash_message_r)
    ac_calldata = [staking_contract.contract_address, facade_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    await facade_admin_contract.set_revenue(*calldata).invoke(signature=[*signature])
    calldata = [uuid4().int, k2.stark_key, 500000, ERC20_CONTRACT_ADDRESS]
    signature = k2.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    ac_calldata = [ledger_contract.contract_address, staking_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    started_at = int(time())
    starknet.set_timestamp(started_at)
    await facade_contract.stake(*calldata).invoke(signature=[*signature])

    ended_at = started_at + 2419229
    starknet.set_timestamp(ended_at)
    calldata = [calldata[0], uuid4().int]
    signature = k2.sign(*calldata, hash_algo=hash_message_r)
    await facade_contract.unstake(*calldata).invoke(signature=[*signature])
    exec_info = await staking_contract.get_staking(calldata[0]).call()
    assert exec_info.result == ((k2.stark_key, 500000, ERC20_CONTRACT_ADDRESS, started_at, ended_at),)
    exec_info = await ledger_contract.get_balance(k2.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (1002807,)
    exec_info = await ledger_contract.get_balance(k.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (997193,)


@pytest.mark.asyncio
async def test_unstake_non_fungible():
    k, k2 = StarkKeyPair(), StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    staking_contract = await starknet.deploy_source(
        'Staking', ledger_contract.contract_address, access_control_contract.contract_address)
    facade_admin_contract = await starknet.deploy_source('StakingFacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'StakingFacade', staking_contract.contract_address, facade_admin_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, 0])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 1000000, ERC20_CONTRACT_ADDRESS, uuid4().int])
    token_id = uuid4().int
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k2.stark_key, token_id, ERC721_CONTRACT_ADDRESS, uuid4().int])

    calldata = [facade_contract.contract_address, ERC721_CONTRACT_ADDRESS, 200, ERC20_CONTRACT_ADDRESS, k.stark_key, uuid4().int]
    signature = k.sign(*calldata, hash_algo=hash_message_r)
    ac_calldata = [staking_contract.contract_address, facade_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    await facade_admin_contract.set_revenue(*calldata).invoke(signature=[*signature])
    calldata = [uuid4().int, k2.stark_key, token_id, ERC721_CONTRACT_ADDRESS]
    signature = k2.sign(calldata[0], *calldata[2:], hash_algo=hash_message_r)
    ac_calldata = [ledger_contract.contract_address, staking_contract.contract_address, 1, uuid4().int]
    ac_signature = k.sign(*ac_calldata)
    await access_control_contract.acl_toggle_access(*ac_calldata).invoke(signature=[*ac_signature])
    started_at = int(time())
    starknet.set_timestamp(started_at)
    await facade_contract.stake(*calldata).invoke(signature=[*signature])

    ended_at = started_at + 2419229
    starknet.set_timestamp(ended_at)
    calldata = [calldata[0], uuid4().int]
    signature = k2.sign(*calldata, hash_algo=hash_message_r)
    await facade_contract.unstake(*calldata).invoke(signature=[*signature])
    exec_info = await staking_contract.get_staking(calldata[0]).call()
    assert exec_info.result == ((k2.stark_key, token_id, ERC721_CONTRACT_ADDRESS, started_at, ended_at),)
    exec_info = await ledger_contract.get_owner(token_id, ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (k2.stark_key,)
    exec_info = await ledger_contract.get_balance(k2.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (5600,)
    exec_info = await ledger_contract.get_balance(k.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (994400,)

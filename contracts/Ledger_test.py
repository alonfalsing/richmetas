from uuid import uuid4

import pytest
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.testing.starknet import Starknet

from richmetas.sign import StarkKeyPair
from util import patch_starknet

L1_CONTRACT_ADDRESS = 0x13095e61fC38a06041f2502FcC85ccF4100FDeFf
ERC20_CONTRACT_ADDRESS = 0x4A26C7daCcC90434693de4b8bede3151884cab89
ERC721_CONTRACT_ADDRESS = 0xfAfC4Ec8ca3Eb374fbde6e9851134816Aada912a
patch_starknet()


@pytest.mark.asyncio
async def test_register_contract():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    exec_info = await ledger_contract.describe(0).call()
    assert exec_info.result == ((1, 0), )

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC20_CONTRACT_ADDRESS, 1, 0])
    exec_info = await ledger_contract.describe(ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == ((1, 0), )

    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('register_contract'),
        [ERC721_CONTRACT_ADDRESS, 2, k.stark_key])
    exec_info = await ledger_contract.describe(ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == ((2, k.stark_key), )


@pytest.mark.asyncio
async def test_deposit():
    k = StarkKeyPair()
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', L1_CONTRACT_ADDRESS, access_control_contract.contract_address)
    await starknet.send_message_to_l2(
        L1_CONTRACT_ADDRESS,
        ledger_contract.contract_address,
        get_selector_from_name('deposit'),
        [k.stark_key, 5050, 0, uuid4().int])
    exec_info = await ledger_contract.get_balance(k.stark_key, 0).call()
    assert exec_info.result == (5050,)

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
    exec_info = await ledger_contract.get_balance(k.stark_key, ERC20_CONTRACT_ADDRESS).call()
    assert exec_info.result == (23130, )

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
    exec_info = await ledger_contract.get_owner(21930, ERC721_CONTRACT_ADDRESS).call()
    assert exec_info.result == (k.stark_key, )

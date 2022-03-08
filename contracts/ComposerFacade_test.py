from uuid import uuid4

import pytest
from eth_account import Account
from more_itertools import repeatfunc
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException

from contracts.util import patch_starknet
from richmetas.sign import StarkKeyPair

patch_starknet()


@pytest.fixture
async def deploy_ledger():
    k = StarkKeyPair()
    l1_contract_address = int(Account.create().address, 0)
    starknet = await Starknet.empty()
    access_control_contract = await starknet.deploy_source('AccessControl', k.stark_key)
    ledger_contract = await starknet.deploy_source(
        'Ledger', l1_contract_address, access_control_contract.contract_address)

    return starknet, access_control_contract, ledger_contract, l1_contract_address, k


@pytest.fixture
async def deploy_composer(deploy_ledger):
    starknet, access_control_contract, ledger_contract, l1_contract_address, k = deploy_ledger
    composer_contract = await starknet.deploy_source('Composer', ledger_contract.contract_address, k.stark_key)
    facade_admin_contract = await starknet.deploy_source('FacadeAdmin', k.stark_key)
    facade_contract = await starknet.deploy_source(
        'ComposerFacade', composer_contract.contract_address, facade_admin_contract.contract_address)
    calldata = [ledger_contract.contract_address, composer_contract.contract_address, 1, uuid4().int]
    signature = k.sign(*calldata)
    await access_control_contract.acl_toggle_access(*calldata).invoke(signature=[*signature])

    return facade_contract, composer_contract, k


@pytest.fixture
async def register_contract(deploy_ledger):
    starknet, _access_control_contract, ledger_contract, l1_contract_address, k = deploy_ledger

    nft_contract_addresses = [int(a.address, 0) for a in repeatfunc(Account.create, 7)]
    k2 = StarkKeyPair()
    for i in range(len(nft_contract_addresses)):
        await starknet.send_message_to_l2(
            l1_contract_address,
            ledger_contract.contract_address,
            get_selector_from_name('register_contract'),
            [nft_contract_addresses[i], 2, k.stark_key if i < 3 else k2.stark_key])

    return nft_contract_addresses, k2


@pytest.fixture
async def deposit(deploy_ledger, register_contract):
    starknet, _access_control_contract, ledger_contract, l1_contract_address, _k = deploy_ledger
    nft_contract_addresses, k2 = register_contract

    tokens = [i.int for i in repeatfunc(uuid4, len(nft_contract_addresses))]
    for i in range(3, len(nft_contract_addresses)):
        await starknet.send_message_to_l2(
            l1_contract_address,
            ledger_contract.contract_address,
            get_selector_from_name('deposit'),
            [k2.stark_key, tokens[i], nft_contract_addresses[i], uuid4().int])

    return tokens,


@pytest.mark.asyncio
async def test_create_stereotype(deploy_composer):
    facade_contract, composer_contract, k = deploy_composer

    stereotype_id = uuid4().int
    k2 = StarkKeyPair()
    await facade_contract.create_stereotype(stereotype_id, k.stark_key, k2.stark_key).invoke()
    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((0, 0, 0, k.stark_key, k2.stark_key, 0),)


@pytest.mark.asyncio
async def test_add_or_remove_token(deploy_composer, register_contract, deposit):
    facade_contract, composer_contract, k = deploy_composer
    nft_contract_addresses, k2 = register_contract
    tokens, = deposit

    stereotype_id = uuid4().int
    await facade_contract.create_stereotype(stereotype_id, k.stark_key, k2.stark_key).invoke()

    for i, io in {0: 2, 3: 1, 4: 1}.items():
        calldata = [tokens[i], nft_contract_addresses[i], io, stereotype_id, uuid4().int]
        signature = k.sign(*calldata)
        await facade_contract.add_token(*calldata).invoke(signature=[*signature])
    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((2, 1, 0, k.stark_key, k2.stark_key, 0),)
    for io, i, j in [(1, 0, 3), (1, 1, 4), (2, 0, 0)]:
        exec_info = await composer_contract.get_token(stereotype_id, io, i).call()
        assert exec_info.result == ((tokens[j], nft_contract_addresses[j]),)

    for i, io in {0: 2, 3: 2, 5: 2}.items():
        calldata = [tokens[i], nft_contract_addresses[i], io, stereotype_id, uuid4().int]
        signature = k.sign(*calldata)
        with pytest.raises(StarkException):
            await facade_contract.add_token(*calldata).invoke(signature=[*signature])
    for i, io in {1: 2, 5: 1}.items():
        calldata = [tokens[i], nft_contract_addresses[i], io, stereotype_id, uuid4().int]
        signature = k.sign(*calldata)
        await facade_contract.add_token(*calldata).invoke(signature=[*signature])
    for i in [0, 4]:
        calldata = [tokens[i], nft_contract_addresses[i], stereotype_id, uuid4().int]
        signature = k.sign(*calldata)
        await facade_contract.remove_token(*calldata).invoke(signature=[*signature])
    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((2, 1, 0, k.stark_key, k2.stark_key, 0),)
    for io, i, j in [(1, 0, 3), (1, 1, 5), (2, 0, 1)]:
        exec_info = await composer_contract.get_token(stereotype_id, io, i).call()
        assert exec_info.result == ((tokens[j], nft_contract_addresses[j]),)


@pytest.mark.asyncio
async def test_activate_stereotype(deploy_composer, register_contract, deposit):
    facade_contract, composer_contract, k = deploy_composer
    nft_contract_addresses, k2 = register_contract
    tokens, = deposit

    stereotype_id = uuid4().int
    await facade_contract.create_stereotype(stereotype_id, k.stark_key, k2.stark_key).invoke()

    calldata = [stereotype_id, uuid4().int]
    signature = k.sign(*calldata)
    with pytest.raises(StarkException):
        await facade_contract.activate_stereotype(*calldata).invoke(signature=[*signature])

    for i, io in {0: 2, 3: 1, 4: 1}.items():
        calldata2 = [tokens[i], nft_contract_addresses[i], io, stereotype_id, uuid4().int]
        signature2 = k.sign(*calldata2)
        await facade_contract.add_token(*calldata2).invoke(signature=[*signature2])
    with pytest.raises(StarkException):
        await facade_contract.activate_stereotype(*calldata).invoke(signature=[*k2.sign(*calldata)])
    await facade_contract.activate_stereotype(*calldata).invoke(signature=[*signature])
    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((2, 1, 0, k.stark_key, k2.stark_key, 1),)


@pytest.mark.asyncio
async def test_install_or_uninstall_token(deploy_composer, register_contract, deposit):
    facade_contract, composer_contract, k = deploy_composer
    nft_contract_addresses, k2 = register_contract
    tokens, = deposit

    stereotype_id = uuid4().int
    await facade_contract.create_stereotype(stereotype_id, k.stark_key, k2.stark_key).invoke()

    for i, io in {0: 2, 3: 1, 4: 1}.items():
        calldata = [tokens[i], nft_contract_addresses[i], io, stereotype_id, uuid4().int]
        signature = k.sign(*calldata)
        await facade_contract.add_token(*calldata).invoke(signature=[*signature])
    calldata = [stereotype_id, uuid4().int]
    signature = k.sign(*calldata)
    await facade_contract.activate_stereotype(*calldata).invoke(signature=[*signature])

    for i in [3, 4]:
        calldata = [k2.stark_key, tokens[i], nft_contract_addresses[i], stereotype_id, uuid4().int]
        signature = k2.sign(*calldata[1:])
        await facade_contract.install_token(*calldata).invoke(signature=[*signature])
    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((2, 1, 2, k.stark_key, k2.stark_key, 1),)
    for i, j in [(0, 3), (1, 4)]:
        exec_info = await composer_contract.get_token(stereotype_id, 3, i).call()
        assert exec_info.result == ((tokens[j], nft_contract_addresses[j]),)

    calldata = [tokens[3], nft_contract_addresses[3], stereotype_id, uuid4().int]
    signature = k2.sign(*calldata)
    await facade_contract.uninstall_token(*calldata).invoke(signature=[*signature])
    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((2, 1, 1, k.stark_key, k2.stark_key, 1),)
    exec_info = await composer_contract.get_token(stereotype_id, 3, 0).call()
    assert exec_info.result == ((tokens[4], nft_contract_addresses[4]),)


@pytest.mark.asyncio
async def test_execute_stereotype(deploy_ledger, deploy_composer, register_contract, deposit):
    _starknet, _access_control_contract, ledger_contract, _l1_contract_address, _k = deploy_ledger
    facade_contract, composer_contract, k = deploy_composer
    nft_contract_addresses, k2 = register_contract
    tokens, = deposit

    stereotype_id = uuid4().int
    await facade_contract.create_stereotype(stereotype_id, k.stark_key, k2.stark_key).invoke()

    for i, io in {0: 2, 1: 2, 3: 1, 4: 1, 5: 1}.items():
        calldata = [tokens[i], nft_contract_addresses[i], io, stereotype_id, uuid4().int]
        signature = k.sign(*calldata)
        await facade_contract.add_token(*calldata).invoke(signature=[*signature])
    calldata = [stereotype_id, uuid4().int]
    signature = k.sign(*calldata)
    await facade_contract.activate_stereotype(*calldata).invoke(signature=[*signature])
    for i in [3, 4]:
        calldata = [k2.stark_key, tokens[i], nft_contract_addresses[i], stereotype_id, uuid4().int]
        signature = k2.sign(*calldata[1:])
        await facade_contract.install_token(*calldata).invoke(signature=[*signature])

    calldata = [stereotype_id, uuid4().int]
    signature = k2.sign(*calldata)
    with pytest.raises(StarkException):
        await facade_contract.execute_stereotype(*calldata).invoke(signature=[*signature])

    calldata2 = [k2.stark_key, tokens[5], nft_contract_addresses[5], stereotype_id, uuid4().int]
    signature2 = k2.sign(*calldata2[1:])
    await facade_contract.install_token(*calldata2).invoke(signature=[*signature2])
    await facade_contract.execute_stereotype(*calldata).invoke(signature=[*signature])

    exec_info = await composer_contract.get_stereotype(stereotype_id).call()
    assert exec_info.result == ((3, 2, 3, k.stark_key, k2.stark_key, 3),)
    for i in [0, 1]:
        exec_info = await ledger_contract.get_owner(tokens[i], nft_contract_addresses[i]).call()
        assert exec_info.result == (k2.stark_key,)

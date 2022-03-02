import asyncio
import logging
from uuid import uuid4

import click
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select, null
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, selectinload
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient

from richmetas.containers import build_container, Container
from richmetas.contracts.starknet import Facade as StarkRichmetas
from richmetas.contracts.starknet.base import Base as BaseContract, BaseFeeder
from richmetas.models import Account, LoginLoad, TokenContract, DescriptionLoad, Blueprint, Balance, BalanceLoad, Token, \
    TokenLoad
from richmetas.models.TokenContract import KIND_ERC20, KIND_ERC721
from richmetas.sign import StarkKeyPair


async def load_descriptions(
        ledger_address: int = Provide[Container.config.ledger_address],
        admin_key: StarkKeyPair = Provide[Container.stark_key],
        gateway: GatewayClient = Provide[Container.gateway],
        async_session: sessionmaker = Provide[Container.async_session]):
    ledger_contract = BaseContract(ledger_address)
    while True:
        async with async_session() as session:
            try:
                contract = (await session.execute(
                    select(TokenContract).
                    join(DescriptionLoad, isouter=True).
                    where(DescriptionLoad.tx_hash == null()).
                    limit(1).
                    options(
                        selectinload(TokenContract.blueprint).
                        selectinload(Blueprint.minter)))).scalar_one()
            except NoResultFound:
                break

            calldata = [
                contract.address,
                KIND_ERC20 if contract.fungible else KIND_ERC721,
                int(contract.blueprint.minter.stark_key) if contract.blueprint else 0,
                uuid4().int]
            signature = [*admin_key.sign(*calldata)]
            tx = await gateway.add_transaction(ledger_contract.invoke('load_description', calldata, signature))
            load = DescriptionLoad(contract=contract, tx_hash=tx['transaction_hash'])
            session.add(load)

            await session.commit()
            logging.warning(f'load_description({calldata[0]}, {calldata[1]}, {calldata[2]})')


async def load_balances(
        ledger_address: int = Provide[Container.config.ledger_address],
        admin_key: StarkKeyPair = Provide[Container.stark_key],
        gateway: GatewayClient = Provide[Container.gateway],
        async_session: sessionmaker = Provide[Container.async_session]):
    ledger_contract = BaseContract(ledger_address)
    while True:
        async with async_session() as session:
            try:
                balance = (await session.execute(
                    select(Balance).
                    join(BalanceLoad, isouter=True).
                    where(Balance.amount > 0).
                    where(BalanceLoad.tx_hash == null()).
                    limit(1).
                    options(
                        selectinload(Balance.account),
                        selectinload(Balance.contract)))).scalar_one()
            except NoResultFound:
                break

            calldata = [
                int(balance.account.stark_key),
                balance.contract.address,
                int(balance.amount),
                uuid4().int]
            signature = [*admin_key.sign(*calldata)]
            tx = await gateway.add_transaction(ledger_contract.invoke('load_balance', calldata, signature))
            load = BalanceLoad(balance=balance, tx_hash=tx['transaction_hash'])
            session.add(load)

            await session.commit()
            logging.warning(f'load_balance({calldata[0]}, {calldata[1]}, {calldata[2]})')


async def load_tokens(
        ledger_address: int = Provide[Container.config.ledger_address],
        legacy_ledger: BaseFeeder = Provide[Container.legacy_ledger],
        admin_key: StarkKeyPair = Provide[Container.stark_key],
        gateway: GatewayClient = Provide[Container.gateway],
        async_session: sessionmaker = Provide[Container.async_session]):
    ledger_contract = BaseContract(ledger_address)
    while True:
        async with async_session() as session:
            try:
                token = (await session.execute(
                    select(Token).
                    join(TokenLoad, isouter=True).
                    where(Token.owner != null()).
                    where(TokenLoad.tx_hash == null()).
                    limit(1).
                    options(
                        selectinload(Token.contract),
                        selectinload(Token.owner)))).scalar_one()
            except NoResultFound:
                break

            origin, = await legacy_ledger.call('get_origin', [int(token.token_id), token.contract.address])
            calldata = [
                int(token.token_id),
                token.contract.address,
                int(token.owner.stark_key),
                origin,
                uuid4().int]
            signature = [*admin_key.sign(*calldata)]
            tx = await gateway.add_transaction(ledger_contract.invoke('load_owner', calldata, signature))
            load = TokenLoad(token=token, tx_hash=tx['transaction_hash'])
            session.add(load)

            await session.commit()
            logging.warning(f'load_token({calldata[0]}, {calldata[1]}, {calldata[2]}, {calldata[3]})')


async def load_ledger():
    await load_descriptions()
    await load_balances()
    await load_tokens()


@inject
async def load_logins(
        gateway: GatewayClient = Provide[Container.gateway],
        richmetas: StarkRichmetas = Provide[Container.stark_richmetas],
        async_session: sessionmaker = Provide[Container.async_session]):
    while True:
        async with async_session() as session:
            try:
                account = (await session.execute(
                    select(Account).
                    join(LoginLoad, isouter=True).
                    where(Account.address != null()).
                    where(LoginLoad.tx_hash == null()).
                    limit(1))).scalar_one()
            except NoResultFound:
                break

            tx = await gateway.add_transaction(
                richmetas.register_account(int(account.stark_key), account.address, uuid4().int))
            load = LoginLoad(account=account, tx_hash=tx['transaction_hash'])
            session.add(load)

            await session.commit()
            logging.warning(f'register_account({account.stark_key}, {account.address})')


@click.group()
def cli():
    build_container()


@cli.command()
def logins():
    asyncio.run(load_logins())


@cli.command()
def ledger():
    asyncio.run(load_ledger())

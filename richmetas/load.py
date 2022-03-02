import asyncio
import logging
from uuid import uuid4

import click
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select, null, true
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.sql import functions
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient

from richmetas.containers import build_container, Container
from richmetas.contracts.starknet import Facade as StarkRichmetas
from richmetas.contracts.starknet.base import Base as BaseContract, BaseFeeder
from richmetas.models import Account, LoginLoad, TokenContract, DescriptionLoad, Blueprint, Balance, BalanceLoad, Token, \
    TokenLoad, LimitOrder, LimitOrderLoad, State
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


async def load_balance(
        user,
        contract,
        amount,
        ledger_contract: BaseContract = Provide[Container.ledger_contract],
        admin_key: StarkKeyPair = Provide[Container.stark_key],
        gateway: GatewayClient = Provide[Container.gateway]):
    calldata = [int(user), contract, int(amount), uuid4().int]
    signature = [*admin_key.sign(*calldata)]

    logging.warning(f'load_balance({calldata[0]}, {calldata[1]}, {calldata[2]}, {calldata[3]})')
    tx = await gateway.add_transaction(ledger_contract.invoke('load_balance', calldata, signature))

    return tx['transaction_hash']


async def load_balances(async_session: sessionmaker = Provide[Container.async_session]):
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

            load = BalanceLoad(balance=balance, tx_hash=await load_balance(
                balance.amount.stark_key, balance.contract.address, balance.amount))
            session.add(load)
            await session.commit()


async def load_token(
        token: Token,
        ledger_contract: BaseContract = Provide[Container.ledger_contract],
        legacy_ledger: BaseFeeder = Provide[Container.legacy_ledger],
        admin_key: StarkKeyPair = Provide[Container.stark_key],
        gateway: GatewayClient = Provide[Container.gateway],
):
    origin, = await legacy_ledger.call('get_origin', [int(token.token_id), token.contract.address])
    calldata = [
        int(token.token_id),
        token.contract.address,
        int(token.owner.stark_key),
        origin,
        uuid4().int]
    signature = [*admin_key.sign(*calldata)]

    logging.warning(f'load_token({calldata[0]}, {calldata[1]}, {calldata[2]}, {calldata[3]})')
    tx = await gateway.add_transaction(ledger_contract.invoke('load_owner', calldata, signature))

    return tx['transaction_hash']


async def load_tokens(async_session: sessionmaker = Provide[Container.async_session]):
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

            load = TokenLoad(token=token, tx_hash=await load_token(token))
            session.add(load)

            await session.commit()


async def load_ledger():
    await load_descriptions()
    await load_balances()
    await load_tokens()


async def load_exchange(
        exchange_contract: BaseContract = Provide[Container.exchange_contract],
        admin_key: StarkKeyPair = Provide[Container.stark_key],
        gateway: GatewayClient = Provide[Container.gateway],
        async_session: sessionmaker = Provide[Container.async_session]):
    while True:
        async with async_session() as session:
            try:
                order = (await session.execute(
                    select(LimitOrder).
                    join(LimitOrderLoad, isouter=True).
                    where(LimitOrderLoad.tx_hash == null()).
                    limit(1).
                    options(
                        selectinload(LimitOrder.user),
                        selectinload(LimitOrder.token).
                        selectinload(Token.contract),
                        selectinload(LimitOrder.quote_contract)))).scalar_one()
            except NoResultFound:
                break

        calldata = [
            int(order.order_id),
            int(order.user.stark_key),
            1 if order.bid else 0,
            order.token.contract.address,
            int(order.token.token_id),
            order.quote_contract.address,
            int(order.quote_amount),
            order.state.value]
        signature = [*admin_key.sign(*calldata)]
        logging.warning(
            f'load_order({calldata[0]}, {calldata[1]}, {calldata[2]}, '
            f'{calldata[3]}, {calldata[4]}, {calldata[5]}, {calldata[6]}, {calldata[7]})')
        tx = await gateway.add_transaction(exchange_contract.invoke('load_order', calldata, signature))
        load = LimitOrderLoad(order=order, tx_hash=tx['transaction_hash'])
        session.add(load)
        if order.state == State.NEW and not order.bid:
            load.tx_hash2 = await load_token(order.token)

        await session.commit()

    async with async_session() as session:
        for contract, balance in await session.execute(
                select(TokenContract, functions.sum(LimitOrder.quote_amount)).
                join(LimitOrder).
                where(LimitOrder.closed_tx == null()).
                where(LimitOrder.bid == true()).
                group_by(TokenContract.id)):
            await load_balance(exchange_contract.address, contract.address, balance)


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
def exchange():
    asyncio.run(load_exchange())


@cli.command()
def ledger():
    asyncio.run(load_ledger())

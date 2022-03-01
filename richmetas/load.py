import asyncio
import logging
from uuid import uuid4

import click
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select, null
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient

from richmetas.containers import build_container, Container
from richmetas.contracts.starknet import Facade as StarkRichmetas
from richmetas.models import Account, LoginLoad


async def load_description():
    ...


async def load_balance():
    ...


async def load_owner():
    ...


async def load_ledger():
    ...


@inject
async def load_logins(
        # old: int,
        gateway: GatewayClient = Provide[Container.gateway],
        # feeder_gateway: FeederGatewayClient = Provide[Container.feeder_gateway],
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

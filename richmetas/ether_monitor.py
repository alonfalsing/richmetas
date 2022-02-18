import asyncio
import logging
from collections.abc import Mapping, Sequence
from decimal import Decimal

import click
import pendulum
from ethereum.abi import decode_abi, decode_hex
from sqlalchemy import select, desc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from web3 import Web3

from richmetas.models import EthBlock, EthEvent, TokenContract, Withdrawal, TokenFlow, FlowType
from richmetas.utils import parse_int, to_checksum_address


class Monitor:
    def __init__(self, w3: Web3, session: sessionmaker, client: FeederGatewayClient, from_address: str, to_address: str):
        self._w3 = w3
        self._session = session
        self._client = client
        self._from_address = from_address
        self._to_address = to_address

    async def run(self):
        addresses = await self._client.get_contract_addresses()
        from_block = 0
        async with self._session() as session:
            try:
                block = (await session.execute(
                    select(EthBlock).
                    order_by(desc(EthBlock.id)).
                    limit(1))).scalar_one()
                from_block = block.id
            except NoResultFound:
                pass

        f = self._w3.eth.filter({
            'address': addresses['Starknet'],
            'topics': [
                # ConsumedMessageToL1
                '0x7a06c571aa77f34d9706c51e5d8122b5595aebeaa34233bfe866f22befb973b1',
                # from_address
                '0x{:064x}'.format(parse_int(self._from_address)),
                # to_address
                '0x{:064x}'.format(parse_int(self._to_address)),
            ],
            'fromBlock': from_block,
        })
        await self.persist(f.get_all_entries())
        while True:
            await self.persist(f.get_new_entries())
            await asyncio.sleep(15)

    async def persist(self, events):
        for e in events:
            body = cast(e)
            logging.warning(body['transactionHash'])

            try:
                async with self._session() as session:
                    block = (await session.execute(
                        select(EthBlock).
                        where(EthBlock.hash == body['blockHash']))).scalar_one()
            except NoResultFound:
                b = self._w3.eth.get_block(body['blockHash'])
                async with self._session() as session:
                    block = EthBlock(
                        id=b.number,
                        hash=b.hash.hex(),
                        timestamp=pendulum.from_timestamp(b.timestamp))

                    session.add(block)
                    await session.commit()

            assert block.id == body['blockNumber']
            async with self._session() as session:
                ee = (await session.execute(
                    select(EthEvent).
                    where(EthEvent.hash == body['transactionHash']).
                    where(EthEvent.log_index == body['logIndex']))).scalar_one_or_none()
                if ee is not None:
                    continue

                ee = EthEvent(
                    hash=body['transactionHash'],
                    block_number=body['blockNumber'],
                    log_index=body['logIndex'],
                    transaction_index=body['transactionIndex'],
                    body=body,
                )
                session.add(ee)

                payload, = decode_abi(['uint256[]'], decode_hex(e.data))
                if payload[0] == 0:
                    _withdraw, address, amount_or_token_id, contract, org, nonce = payload
                    token_contract = (await session.execute(
                        select(TokenContract).
                        where(TokenContract.address == to_checksum_address(contract)))).scalar_one()
                    if token_contract.fungible:
                        withdrawal = (await session.execute(
                            select(Withdrawal).
                            where(Withdrawal.amount == Decimal(amount_or_token_id)).
                            where(Withdrawal.address == to_checksum_address(address)).
                            where(Withdrawal.nonce == Decimal(nonce)))).scalar_one()
                        withdrawal.event = ee
                    else:
                        token_flow = (await session.execute(
                            select(TokenFlow).
                            where(TokenFlow.type == FlowType.WITHDRAWAL.value).
                            where(TokenFlow.address == to_checksum_address(address)).
                            where(TokenFlow.mint == bool(org)).
                            where(TokenFlow.nonce == Decimal(nonce)))).scalar_one()
                        token_flow.event = ee

                await session.commit()


def cast(x):
    if isinstance(x, str):
        return x
    if isinstance(x, bytes):
        return x.hex()
    if isinstance(x, Sequence):
        return [cast(v) for v in x]
    if isinstance(x, Mapping):
        return dict([(k, cast(v)) for k, v in x.items()])
    return x


@click.command()
def cli():
    from decouple import config
    from web3.middleware import geth_poa_middleware
    from richmetas.globals import async_session, feeder_gateway_client

    w3 = Web3()
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    m = Monitor(
        w3,
        async_session,
        feeder_gateway_client,
        config('STARK_RICHMETAS_CONTRACT_ADDRESS'),
        config('ETHER_RICHMETAS_CONTRACT_ADDRESS'),
    )
    asyncio.run(m.run())

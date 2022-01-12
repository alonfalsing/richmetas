import asyncio
import logging
from asyncio import Future
from datetime import datetime, timezone

import click
from services.external_api.base_client import BadRequest
from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient

from richmetas.models import Block, Transaction, StarkContract


class BlockCache:
    def __init__(self, async_session: sessionmaker):
        self._lo = -1
        self._blocks = []
        self._async_session = async_session

    async def hit(self, block_number):
        lo = int(block_number / 1000)
        if self._lo != lo:
            self._lo = lo
            lo *= 1000

            async with self._async_session() as session:
                blocks = await session.execute(
                    select(Block.id).
                    where(lo <= Block.id).
                    where(Block.id < lo + 1000))
                self._blocks = [b for b, in blocks]

        return block_number in self._blocks


class Crawler:
    def __init__(self, feeder_gateway: FeederGatewayClient, async_session: sessionmaker, cooldown: float):
        self._feeder_gateway = feeder_gateway
        self._async_session = async_session
        self._block_cache = BlockCache(async_session)
        self._cooldown = cooldown
        self._blocks: set[int] = set()
        self._waits: dict[int, list[Future]] = dict()

    async def wait(self, block_number: int):
        if block_number in self._blocks:
            return

        f = Future()
        fs = self._waits.get(block_number, [])
        fs.append(f)
        self._waits[block_number] = fs

        await f

    async def run(self, thru=None):
        block = await self._feeder_gateway.get_block(block_hash=thru)
        i = j = block['block_number'] + 1

        loop = asyncio.get_running_loop()
        cd = loop.time()
        while True:
            if thru is None and cd < loop.time():
                try:
                    await self._crawl(j)
                    j += 1

                    continue
                except BadRequest:
                    cd = loop.time() + self._cooldown

            if i > 0:
                await self._crawl(i - 1)
                i -= 1

                continue

            await asyncio.sleep(self._cooldown)

    async def purge(self, dry=False):
        block_number, block_number0, error = 0, -1, -1
        while block_number0 < block_number:
            if error is not None:
                block_number, error = error, None

            block_number0 = block_number
            async with self._async_session() as session:
                async for block in (await session.stream(
                        select(Block).
                        where(~Block._document['status'].astext.in_(['ACCEPTED_ON_L1', 'ACCEPTED_ONCHAIN'])).
                        where(Block.id > block_number).
                        order_by(Block.id).
                        limit(20))).scalars():
                    logging.warning(f"purge(block_hash={block.hash}, block_number={block.id})")
                    block_number = block.id

                    try:
                        document = await self._feeder_gateway.get_block(block_number=block.id)
                    except BadRequest as e:
                        logging.warning(e)
                        if error is None:
                            error = block.id
                        continue

                    if document['block_hash'] != block.hash or document['status'] in ['ABORTED']:
                        logging.warning(f"abort(block_hash={block.hash}, block_number={block.id})")
                    if dry:
                        continue

                    block._document = document
                    if document['block_hash'] != block.hash or document['status'] in ['ABORTED']:
                        await session.execute(delete(Transaction).where(Transaction.block == block))
                        session.delete(block)

                await session.commit()

    async def _crawl(self, block_number: int):
        if await self._block_cache.hit(block_number):
            return

        logging.warning(f'crawl_block(block_number={block_number})')
        await self._persist(await self._feeder_gateway.get_block(block_number=block_number))
        self._blocks.add(block_number)
        for each in self._waits.pop(block_number, []):
            each.set_result(True)

    async def _persist(self, document):
        async with self._async_session() as session:
            block = Block(
                id=document['block_number'],
                hash=document['block_hash'],
                timestamp=datetime.fromtimestamp(document['timestamp'], timezone.utc),
                _document=document)
            session.add(block)

            for receipt, transaction in zip(document['transaction_receipts'], document['transactions']):
                assert receipt['transaction_hash'] == transaction['transaction_hash']
                try:
                    contract, = (await session.execute(
                        select(StarkContract).
                        where(StarkContract.address == transaction['contract_address']))).one()
                except NoResultFound:
                    contract = StarkContract(address=transaction['contract_address'])
                    session.add(contract)

                tx = Transaction(
                    hash=transaction['transaction_hash'],
                    block=block,
                    transaction_index=receipt['transaction_index'],
                    type=transaction['type'],
                    contract=contract,
                    entry_point_selector=transaction.get('entry_point_selector'),
                    entry_point_type=transaction.get('entry_point_type'),
                    calldata=transaction['calldata' if transaction['type'] != 'DEPLOY' else 'constructor_calldata'])
                session.add(tx)

            await session.commit()


def build():
    from richmetas.globals import async_session, feeder_gateway_client

    return Crawler(feeder_gateway_client, async_session, 15)


@click.group(invoke_without_command=True)
@click.option('--thru')
@click.pass_context
def crawl(ctx, thru):
    if not ctx.invoked_subcommand:
        asyncio.run(build().run(thru))


@crawl.command()
@click.option('--dry', is_flag=True)
def purge(dry):
    asyncio.run(build().purge(dry))

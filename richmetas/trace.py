import asyncio
import logging

import click
from aiohttp import web, ClientError
from aiohttp.web_request import Request
from sqlalchemy import select
from starkware.starknet.public.abi import get_selector_from_name

from richmetas.models import StarkContract, Transaction, Block
from richmetas.models.Transaction import TransactionSchema
from richmetas.utils import parse_int


async def next_transaction(request, address: str, function: str, block_number: int):
    stmt = select(Transaction). \
        join(Transaction.contract). \
        where(StarkContract.address == address). \
        order_by(Transaction.block_number). \
        order_by(Transaction.transaction_index)
    if function != '*':
        stmt = stmt.where(Transaction.entry_point_selector == hex(get_selector_from_name(function)))

    while True:
        async with request.config_dict['async_session']() as session:
            bs = range(block_number, block_number + 8000)
            blocks = (await session.execute(
                select(Block.id).
                where(bs.start <= Block.id).
                where(Block.id < bs.stop).
                order_by(Block.id))).scalars().all()

            sentinel = block_number + len(blocks)
            for i, j in zip(bs, blocks):
                if i != j:
                    sentinel = i
                    break

        if block_number == sentinel:
            await request.config_dict['crawler'].wait(block_number)
            continue

        for b in range(block_number, sentinel, 200):
            async with request.config_dict['async_session']() as session:
                s = stmt. \
                    where(b <= Transaction.block_number). \
                    where(Transaction.block_number < min(b + 200, sentinel))
                for tx in (await session.execute(s)).scalars():
                    yield tx

        block_number = sentinel


async def subscribe_contract(request: Request):
    address = request.match_info['address']
    function = request.match_info['function']
    block_number = parse_int(request.query.get('b', '0'))

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for tx in next_transaction(request, address, function, block_number):
        await ws.send_json(TransactionSchema().dump(tx))

    return ws


async def start(app, port: int):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    await site.start()

    names = sorted(str(s.name) for s in runner.sites)
    print(
        "======== Running on {} ========\n"
        "(Press CTRL+C to quit)".format(", ".join(names))
    )

    while True:
        try:
            await asyncio.create_task(app['crawler'].run())
        except ClientError as e:
            logging.warning(e)


@click.command()
@click.option('--port', default=3999, type=int)
def cli(port: int):
    from richmetas.globals import async_session
    from richmetas.crawl import build

    app = web.Application()
    app['async_session'] = async_session
    app['crawler'] = build()
    app.add_routes([web.get('/{address}/{function}', subscribe_contract)])

    asyncio.run(start(app, port))

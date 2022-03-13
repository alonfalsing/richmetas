import asyncio
import logging
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

import aiohttp
import click
from dependency_injector.wiring import Provide, inject
from sqlalchemy import select, update, desc, null
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import functions
from web3 import Web3

from richmetas.containers import Container, build_container
from richmetas.contracts import ERC20, ERC721Metadata
from richmetas.contracts.starknet import Facade as StarkRichmetas
from richmetas.contracts.starknet.base import Base as BaseContract
from richmetas.contracts.starknet.composer import Arm
from richmetas.globals import async_session, feeder_gateway_client
from richmetas.models import Account, TokenContract, Token, LimitOrder, Block, StarkContract, Blueprint, Transfer, \
    TokenFlow, FlowType, Withdrawal, Deposit
from richmetas.models.LimitOrder import Side
from richmetas.models.TokenContract import KIND_ERC721
from richmetas.models.Transaction import Transaction, TYPE_DEPLOY
from richmetas.services import TransferService
from richmetas.utils import to_checksum_address, parse_int, ZERO_ADDRESS, Status


class RichmetasInterpreter:
    @inject
    def __init__(
            self,
            session: AsyncSession,
            client: aiohttp.ClientSession,
            w3: Web3,
            ledger_address: int = Provide[Container.config.ledger_address],
            ledger_facade_address: int = Provide[Container.config.ledger_facade_address],
            exchange_facade_address: int = Provide[Container.config.exchange_facade_address],
            composer_facade_address: int = Provide[Container.config.composer_facade_address],
            login_facade_admin_address: int = Provide[Container.config.login_facade_admin_address]):
        from starkware.starknet.public.abi import get_selector_from_name

        self.session = session
        self.client = client
        self.w3 = w3
        self._transfer_service = TransferService(self.session)
        self._instructions = dict([
            (hex(get_selector_from_name(f)), (hex(a), self.__getattribute__(f)))
            for (a, f) in [
                (ledger_address, 'register_contract'),
                (login_facade_admin_address, 'register_account'),
                (ledger_facade_address, 'mint'),
                (ledger_facade_address, 'withdraw'),
                (ledger_address, 'deposit'),
                (ledger_facade_address, 'transfer'),
                (exchange_facade_address, 'create_order'),
                (exchange_facade_address, 'fulfill_order'),
                (exchange_facade_address, 'cancel_order'),
                (composer_facade_address, 'install_token'),
                (composer_facade_address, 'uninstall_token'),
                (composer_facade_address, 'execute_stereotype'),
                (composer_facade_address, 'solve_stereotype'),
            ]
        ])

    @inject
    async def exec(self, tx: Transaction):
        if tx.entry_point_selector in self._instructions:
            a, f = self._instructions[tx.entry_point_selector]
            assert a == tx.contract.address
            await f(tx)

    async def register_contract(self, tx: Transaction):
        logging.warning(f'register_contract')
        _from_address, contract, kind, mint = tx.calldata
        address = to_checksum_address(contract)
        try:
            token_contract = (await self.session.execute(
                select(TokenContract).
                where(TokenContract.address == address).
                options(selectinload(TokenContract.blueprint).
                        selectinload(Blueprint.minter)))).scalar_one()
            assert token_contract.fungible == (int(kind) != KIND_ERC721)
            if not token_contract.fungible:
                assert token_contract.blueprint.minter.stark_key == Decimal(mint)
        except NoResultFound:
            fungible = int(kind) != KIND_ERC721
            blueprint = None
            if not fungible:
                minter = await self.lift_account(mint)
                blueprint = Blueprint(minter=minter)
                self.session.add(blueprint)

            token_contract = TokenContract(
                address=to_checksum_address(contract),
                fungible=fungible,
                blueprint=blueprint)
            self.session.add(self.lift_contract(token_contract))

    async def register_account(self, tx: Transaction):
        logging.warning(f'register_account')
        _contract, user, address, _nonce = tx.calldata
        await self.lift_account(user, address)

    async def mint(self, tx: Transaction):
        logging.warning(f'mint')
        user, token_id, contract, _nonce = tx.calldata
        await self._mint(user, token_id, contract, tx)

    async def withdraw(self, tx: Transaction):
        logging.warning(f'withdraw')
        user, amount_or_token_id, contract, address, nonce = tx.calldata
        account = await self._transfer_service.lift_account(parse_int(user))
        token = await self.lift_token(amount_or_token_id, contract)
        if token:
            assert token.owner == account
            for receipt in tx.block._document['transaction_receipts']:
                if receipt['transaction_hash'] == tx.hash:
                    break

            flow = TokenFlow(
                transaction=tx,
                type=FlowType.WITHDRAWAL.value,
                token=token,
                from_account=token.owner,
                address=to_checksum_address(address),
                nonce=parse_int(nonce),
                mint=receipt['l2_to_l1_messages'][0]['payload'][4] == '1',
            )
            self.session.add(flow)

            token.owner = None
            token.latest_tx = tx
        else:
            token_contract = (await self.session.execute(
                select(TokenContract).
                where(TokenContract.address == to_checksum_address(contract)))).scalar_one()
            balance = await self._transfer_service.lift_balance(account, token_contract)
            withdrawal = Withdrawal(
                transaction=tx,
                balance=balance,
                amount=parse_int(amount_or_token_id),
                address=to_checksum_address(address),
                nonce=parse_int(nonce),
            )
            self.session.add(withdrawal)
            balance.amount -= withdrawal.amount

    async def deposit(self, tx: Transaction):
        logging.warning(f'deposit')
        _from_address, user, amount_or_token_id, contract, _nonce = tx.calldata
        account = await self.lift_account(user)
        token = await self.lift_token(amount_or_token_id, contract)
        if token:
            token.owner = account
            token.latest_tx = tx

            flow = TokenFlow(
                transaction=tx,
                type=FlowType.DEPOSIT.value,
                token=token,
                to_account=account,
            )
            self.session.add(flow)
        else:
            token_contract = (await self.session.execute(
                select(TokenContract).
                where(TokenContract.address == to_checksum_address(contract)))).scalar_one()
            balance = await self._transfer_service.lift_balance(account, token_contract)
            deposit = Deposit(
                transaction=tx,
                balance=balance,
                amount=parse_int(amount_or_token_id),
            )
            self.session.add(deposit)
            balance.amount += deposit.amount

    async def transfer(self, tx: Transaction):
        logging.warning(f'transfer')
        from_address, to_address, amount_or_token_id, contract, nonce = tx.calldata
        if (await self._flow(from_address, to_address, amount_or_token_id, contract, tx)) is None:
            status = tx.block._document['status']
            try:
                transfer = (await self.session.execute(
                    select(Transfer).where(Transfer.hash == tx.hash))).scalar_one()
                transfer.status = status
            except NoResultFound:
                token_contract = (await self.session.execute(
                    select(TokenContract).
                    where(TokenContract.address == to_checksum_address(contract)))).scalar_one()
                await TransferService(self.session).transfer(
                    tx.hash,
                    parse_int(from_address),
                    parse_int(to_address),
                    parse_int(amount_or_token_id),
                    token_contract,
                    parse_int(nonce),
                    status=status)

    async def create_order(self, tx: Transaction):
        logging.warning(f'create_order')
        order_id, user, bid, base_contract, base_token_id, quote_contract, quote_amount = tx.calldata
        account = await self.lift_account(user)
        token = await self.lift_token(base_token_id, base_contract)
        quote_contract, = (await self.session.execute(
            select(TokenContract).where(TokenContract.address == to_checksum_address(quote_contract)))).one()

        limit_order = LimitOrder(
            order_id=Decimal(order_id),
            user=account,
            bid=parse_int(bid) == Side.BID,
            token=token,
            quote_contract=quote_contract,
            quote_amount=Decimal(quote_amount),
            tx=tx)
        self.session.add(limit_order)

        if not limit_order.bid:
            assert token.owner == account
            token.ask = limit_order
        else:
            balance = await self._transfer_service.lift_balance(account, quote_contract)
            balance.amount -= limit_order.quote_amount

    async def fulfill_order(self, tx: Transaction):
        logging.warning(f'fulfill_order')
        order_id, user, _nonce = tx.calldata
        limit_order, = (await self.session.execute(
            select(LimitOrder).
            where(LimitOrder.order_id == Decimal(order_id)).
            options(selectinload(LimitOrder.token),
                    selectinload(LimitOrder.user),
                    selectinload(LimitOrder.quote_contract)))).one()
        limit_order.closed_tx = tx
        limit_order.fulfilled = True

        token = limit_order.token
        token.latest_tx = tx
        token.ask = None

        user = await self.lift_account(user)
        if limit_order.bid:
            token.owner = limit_order.user
            balance = await self._transfer_service.lift_balance(user, limit_order.quote_contract)
            balance.amount += limit_order.quote_amount
        else:
            token.owner = user
            balance = await self._transfer_service.lift_balance(user, limit_order.quote_contract)
            balance.amount -= limit_order.quote_amount
            balance = await self._transfer_service.lift_balance(limit_order.user, limit_order.quote_contract)
            balance.amount += limit_order.quote_amount

    async def cancel_order(self, tx: Transaction):
        logging.warning(f'cancel_order')
        order_id, nonce_ = tx.calldata
        limit_order, = (await self.session.execute(
            select(LimitOrder).
            where(LimitOrder.order_id == Decimal(order_id)).
            options(selectinload(LimitOrder.token)))).one()
        limit_order.closed_tx = tx
        limit_order.fulfilled = False

        if limit_order.bid:
            balance = await self._transfer_service.lift_balance(limit_order.user, limit_order.quote_contract)
            balance.amount += limit_order.quote_amount
        else:
            limit_order.token.ask = None

    @inject
    async def install_token(
            self,
            tx: Transaction,
            composer: BaseContract = Provide[Container.composer_contract]):
        user, token_id, contract, stereotype_id, _nonce = tx.calldata
        if (await self._solve_stereotype('install_token', stereotype_id, tx)) > 0:
            return

        logging.warning(f'install_token')
        await self._flow(user, composer.address, token_id, contract, tx, extra=dict(
            stereotype_id=stereotype_id,
            owner=user,
            _f='install_token',
        ))

    @inject
    async def uninstall_token(
            self,
            tx: Transaction,
            composer: BaseContract = Provide[Container.composer_contract]):
        token_id, contract, stereotype_id, _nonce = tx.calldata
        if (await self._solve_stereotype('uninstall_token', stereotype_id, tx)) > 0:
            return

        logging.warning(f'uninstall_token')
        flow = (await self.session.execute(
            select(TokenFlow).
            join(TokenFlow.token).
            join(Token.contract).
            join(TokenFlow.transaction).
            where(Token.token_id == Decimal(parse_int(token_id))).
            where(TokenContract.address == to_checksum_address(contract)).
            order_by(desc(Transaction.block_number)).
            order_by(desc(Transaction.transaction_index)).
            limit(1))).scalar_one()
        assert flow.extra['_f'] == 'install_token'
        await self._flow(composer.address, flow.extra['owner'], token_id, contract, tx, extra=dict(
            stereotype_id=stereotype_id,
            _f='uninstall_token',
        ))

    @inject
    async def execute_stereotype(
            self,
            tx: Transaction,
            richmetas: StarkRichmetas = Provide[Container.stark_richmetas]):
        stereotype_id, _nonce = tx.calldata
        if (await self._solve_stereotype('execute_stereotype', stereotype_id, tx)) > 0:
            return

        logging.warning(f'execute_stereotype')
        stereotype = await richmetas.get_stereotype(stereotype_id)
        for i in range(stereotype.outputs):
            token = await richmetas.get_token(stereotype_id, Arm.OUTPUT.value, i)
            await self._mint(stereotype.user, token.token_id, token.contract, tx, extra=dict(
                stereotype_id=stereotype_id,
                _f='execute_stereotype',
            ))

    async def solve_stereotype(self, tx: Transaction):
        await self._solve_stereotype('solve_stereotype', tx.calldata[0], tx)

    @inject
    async def _solve_stereotype(
            self,
            f,
            stereotype_id,
            tx: Transaction,
            ledger_contract: BaseContract = Provide[Container.ledger_contract]):
        from starkware.starknet.public.abi import get_selector_from_name

        n = 0
        for event in tx.events:
            if parse_int(event['from_address']) != ledger_contract.address:
                continue

            n += 1
            selector = parse_int(event['keys'][0])
            if selector == get_selector_from_name('transfer_event'):
                logging.warning(f'{f}.transfer')
                from_address, to_address, amount_or_token_id, contract = event['data']
                await self._flow(from_address, to_address, amount_or_token_id, contract, tx, extra=dict(
                    stereotype_id=stereotype_id,
                    owner=from_address,
                    _f=f,
                ))
            if selector == get_selector_from_name('mint_event'):
                logging.warning(f'{f}.mint')
                user, token, contract = event['data']
                await self._mint(user, token, contract, tx, extra=dict(
                    stereotype_id=stereotype_id,
                    _f=f,
                ))

        return n

    async def _mint(self, to_address, token_id, contract, tx: Transaction, extra=None):
        token = await self.lift_token(token_id, contract)
        token.latest_tx = tx

        token.owner = await self.lift_account(to_address)
        flow = TokenFlow(
            transaction=tx,
            type=FlowType.MINT.value,
            token=token,
            to_account=token.owner,
            extra=extra or null(),
        )
        self.session.add(flow)

    async def _flow(self, from_address, to_address, token_id, contract, tx: Transaction, extra=None):
        token = await self.lift_token(token_id, contract)
        if token:
            from_account = await self.lift_account(from_address)
            to_account = await self.lift_account(to_address)

            assert token.owner == from_account
            token.owner = to_account
            token.latest_tx = tx

            flow = TokenFlow(
                transaction=tx,
                type=FlowType.TRANSFER.value,
                token=token,
                from_account=from_account,
                to_account=to_account,
                extra=extra or null(),
            )
            self.session.add(flow)

        return token

    async def lift_account(self, user: str, address: Optional[str] = None) -> Account:
        user = Decimal(user)

        try:
            account, = (await self.session.execute(
                select(Account).
                where(Account.stark_key == user))).one()
        except NoResultFound:
            account = Account(stark_key=user)
            self.session.add(account)

        if address:
            account.address = to_checksum_address(address)

        return account

    async def lift_token(self, token_id: str, contract: str) -> Optional[Token]:
        token_id = Decimal(token_id)
        contract = to_checksum_address(contract)

        token_contract, = (await self.session.execute(
            select(TokenContract).where(TokenContract.address == contract))).one()
        if token_contract.fungible:
            return None

        try:
            token, = (await self.session.execute(
                select(Token).
                where(Token.token_id == token_id).
                where(Token.contract == token_contract).
                options(selectinload(Token.owner)))).one()
        except NoResultFound:
            token = Token(contract=token_contract, token_id=token_id, nonce=0)
            self.session.add(token)

        token.token_uri = urljoin(token_contract.base_uri, str(token_id)) if token_contract.base_uri else \
            ERC721Metadata(token_contract.address, self.w3).token_uri(int(token_id))
        from aiohttp import ClientError
        try:
            async with self.client.get(token.token_uri) as resp:
                token.asset_metadata = await resp.json()

                ERC721Metadata.validate(token.asset_metadata)
                token.name = token.asset_metadata['name']
                token.description = token.asset_metadata['description']
                token.image = token.asset_metadata['image']
        except ClientError as e:
            logging.warning(e)

        return token

    def lift_contract(self, token_contract: TokenContract) -> TokenContract:
        if token_contract.address == ZERO_ADDRESS:
            token_contract.name, token_contract.symbol, token_contract.decimals = 'Ether', 'ETH', 18

            return token_contract

        contract = ERC20(token_contract.address, self.w3) if token_contract.fungible else \
            ERC721Metadata(token_contract.address, self.w3)
        try:
            token_contract.name, token_contract.symbol, token_contract.decimals \
                = contract.identify()
        except ValueError:
            pass

        return token_contract


@inject
async def interpret(
        ledger_address: int = Provide[Container.config.ledger_address],
        ledger_facade_address: int = Provide[Container.config.ledger_facade_address],
        exchange_facade_address: int = Provide[Container.config.exchange_facade_address],
        composer_facade_address: int = Provide[Container.config.composer_facade_address],
        login_facade_admin_address: int = Provide[Container.config.login_facade_admin_address]):
    async with async_session() as session:
        try:
            (await session.execute(
                select(TokenContract).where(TokenContract.address == ZERO_ADDRESS))).one()
        except NoResultFound:
            session.add(TokenContract(
                address=ZERO_ADDRESS,
                fungible=True,
                name='Ether',
                symbol='ETH',
                decimals=18))
            await session.commit()

    addresses = [*map(hex, [
        ledger_address,
        ledger_facade_address,
        exchange_facade_address,
        composer_facade_address,
        login_facade_admin_address])]
    while True:
        async with async_session() as session:
            block_counters = (await session.execute(
                select(
                    StarkContract.address,
                    functions.coalesce(
                        StarkContract.block_counter,
                        Transaction.block_number)).
                select_from(StarkContract).
                join(StarkContract.transactions).
                where(Transaction.type == TYPE_DEPLOY).
                where(StarkContract.address.in_(addresses)))).all()
            if len(block_counters) < len(addresses):
                logging.warning('Failed to find "DEPLOY"')
                await asyncio.sleep(15)
                continue

            block_counter = min([b for _a, b in block_counters])
            try:
                block, = (await session.execute(
                    select(Block).where(Block.id == block_counter))).one()
            except NoResultFound:
                logging.warning('Failed to find block')
                await asyncio.sleep(15)
                continue

            active_addresses = [a for a, b in block_counters if b == block_counter]
            async with aiohttp.ClientSession() as client:
                interpreter = RichmetasInterpreter(session, client, Web3())
                for tx, in await session.execute(
                        select(Transaction).
                        join(Transaction.contract).
                        where(Transaction.block == block).
                        where(StarkContract.address.in_(active_addresses)).
                        order_by(Transaction.transaction_index).
                        options(selectinload(Transaction.contract))):
                    logging.warning(f'interpret(tx={tx.hash})')
                    await interpreter.exec(tx)

            await session.execute(
                update(StarkContract).
                where(StarkContract.address.in_(active_addresses)).
                values(block_counter=block_counter + 1))

            await flush_transfers(session)
            await session.commit()


@inject
async def flush_transfers(
        session: AsyncSession,
        richmetas: StarkRichmetas = Provide[Container.stark_richmetas]):
    for transfer in (await session.execute(
            select(Transfer).
            where(Transfer.status.in_([Status.NOT_RECEIVED.value, Status.RECEIVED.value])).
            limit(20).
            options(
            selectinload(Transfer.from_account),
            selectinload(Transfer.to_account),
            selectinload(Transfer.contract)))).scalars():
        status = (await feeder_gateway_client.get_transaction_status(tx_hash=transfer.hash))['tx_status']
        if status == Status.NOT_RECEIVED.value:
            logging.warning(f'transfer(hash={transfer.hash})')
            await richmetas.transfer(
                int(transfer.from_account.stark_key),
                int(transfer.to_account.stark_key),
                int(transfer.amount),
                transfer.contract.address,
                int(transfer.nonce),
                [int(transfer.signature_r), int(transfer.signature_s)])
        elif status == Status.REJECTED.value:
            logging.warning(f'reject(hash={transfer.hash})')
            await TransferService(session).reject(transfer)
        else:
            logging.warning(f'update(hash={transfer.hash}, status={status})')
            transfer.status = status


@click.command()
def cli():
    build_container()
    asyncio.run(interpret())

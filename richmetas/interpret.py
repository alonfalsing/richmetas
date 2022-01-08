import asyncio
import logging
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

import aiohttp
import click
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from web3 import Web3

from richmetas.contracts import ERC20, ERC721Metadata
from richmetas.models import Account, TokenContract, Token, LimitOrder, Block, StarkContract, Blueprint, Transfer
from richmetas.models.LimitOrder import Side
from richmetas.models.TokenContract import KIND_ERC721
from richmetas.models.Transaction import Transaction, TYPE_DEPLOY
from richmetas.globals import async_session
from richmetas.services import TransferService
from richmetas.utils import to_checksum_address, parse_int, ZERO_ADDRESS


class RichmetasInterpreter:
    def __init__(self, session: AsyncSession, client: aiohttp.ClientSession, w3: Web3):
        self.session = session
        self.client = client
        self.w3 = w3
        self._transfer_service = TransferService(self.session)

    async def exec(self, tx: Transaction):
        from starkware.starknet.public.abi import get_selector_from_name

        instructions = dict([
            ('0x%x' % get_selector_from_name(f), self.__getattribute__(f))
            for f in [
                'register_contract',
                'register_client',
                'mint',
                'withdraw',
                'deposit',
                'transfer',
                'create_order',
                'fulfill_order',
                'cancel_order',
            ]
        ])
        try:
            await instructions[tx.entry_point_selector](tx)
        except KeyError:
            pass

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

    async def register_client(self, tx: Transaction):
        logging.warning(f'register_client')
        user, address, _nonce = tx.calldata
        await self.lift_account(user, address)

    async def mint(self, tx: Transaction):
        logging.warning(f'mint')
        user, token_id, contract, _nonce = tx.calldata
        token = await self.lift_token(token_id, contract)
        token.latest_tx = tx

        token.owner = await self.lift_account(user)

    async def withdraw(self, tx: Transaction):
        logging.warning(f'withdraw')
        user, amount_or_token_id, contract, _address, _nonce = tx.calldata
        token = await self.lift_token(amount_or_token_id, contract)
        if token:
            token.owner = None
            token.latest_tx = tx
        else:
            token_contract = (await self.session.execute(
                select(TokenContract).
                where(TokenContract.address == to_checksum_address(contract)))).scalar_one()
            account = await self._transfer_service.lift_account(parse_int(user))
            balance = await self._transfer_service.lift_balance(account, token_contract)
            balance.amount -= parse_int(amount_or_token_id)

    async def deposit(self, tx: Transaction):
        logging.warning(f'deposit')
        _from_address, user, amount_or_token_id, contract, _nonce = tx.calldata
        account = await self.lift_account(user)
        token = await self.lift_token(amount_or_token_id, contract)
        if token:
            token.owner = account
            token.latest_tx = tx
        else:
            token_contract = (await self.session.execute(
                select(TokenContract).
                where(TokenContract.address == to_checksum_address(contract)))).scalar_one()
            balance = await self._transfer_service.lift_balance(account, token_contract)
            balance.amount += parse_int(amount_or_token_id)

    async def transfer(self, tx: Transaction):
        logging.warning(f'transfer')
        from_address, to_address, amount_or_token_id, contract, nonce = tx.calldata
        token = await self.lift_token(amount_or_token_id, contract)
        if token:
            from_account = await self.lift_account(from_address)
            to_account = await self.lift_account(to_address)

            assert token.owner == from_account
            token.owner = to_account
            token.latest_tx = tx
        else:
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
            user = await self.lift_account(user)
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
        async with self.client.get(token.token_uri) as resp:
            token.asset_metadata = await resp.json()

            ERC721Metadata.validate(token.asset_metadata)
            token.name = token.asset_metadata['name']
            token.description = token.asset_metadata['description']
            token.image = token.asset_metadata['image']

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


async def interpret(address: str):
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

    while True:
        async with async_session() as session:
            try:
                contract, = (await session.execute(
                    select(StarkContract).where(StarkContract.address == address))).one()
            except NoResultFound:
                logging.warning('Failed to find contract')
                await asyncio.sleep(15)
                continue

            if contract.block_counter is None:
                try:
                    tx, = (await session.execute(
                        select(Transaction).
                        where(Transaction.contract == contract).
                        where(Transaction.type == TYPE_DEPLOY).
                        options(selectinload(Transaction.block)))).one()

                    contract.block_counter = tx.block.id
                except NoResultFound:
                    logging.warning('Failed to find "DEPLOY"')
                    await asyncio.sleep(15)
                    continue

            try:
                block, = (await session.execute(
                    select(Block).where(Block.id == contract.block_counter))).one()
            except NoResultFound:
                logging.warning('Failed to find block')
                await asyncio.sleep(15)
                continue

            async with aiohttp.ClientSession() as client:
                interpreter = RichmetasInterpreter(session, client, Web3())
                for tx, in await session.execute(
                        select(Transaction).
                        where(Transaction.block == block).
                        where(Transaction.contract == contract).
                        order_by(Transaction.transaction_index)):
                    logging.warning(f'interpret(tx={tx.hash})')
                    await interpreter.exec(tx)

            contract.block_counter += 1
            await session.commit()


@click.command()
@click.argument('contract')
def cli(contract: str):
    asyncio.run(interpret(contract))

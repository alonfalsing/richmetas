import functools
from decimal import Decimal
from typing import Union

import click
import pendulum
import pkg_resources
import pyrsistent
from aiohttp import web
from aiohttp.web_request import Request
from aiojobs.aiohttp import setup, spawn
from decouple import config
from eth_account import Account
from openapi_core import create_spec
from rororo import OperationTableDef, setup_openapi, openapi_context
from services.external_api.base_client import RetryConfig
from sqlalchemy import select, desc, null, false, true
from sqlalchemy.exc import NoResultFound, IntegrityError, MultipleResultsFound
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy.sql import functions
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash
from starkware.crypto.signature.signature import verify
from starkware.starknet.definitions.general_config import StarknetGeneralConfig, StarknetChainId
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient
from web3 import Web3

from richmetas import utils
from richmetas.contracts import Forwarder, ReqSchema, StarkRichmetas, LimitOrder, EtherRichmetas, ContractKind
from richmetas.services import TransferService
from richmetas.utils import parse_int, Status

operations = OperationTableDef()


@operations.register
async def get_contracts(request: Request):
    return web.json_response({
        'main': request.config_dict['forwarder'].to_address,
        'forwarder': request.config_dict['forwarder'].address,
    })


@operations.register
async def register_client(request: Request):
    with openapi_context(request) as context:
        address = utils.to_checksum_address(context.data['address'])
        message_hash = pedersen_hash(
            parse_int(address),
            pedersen_hash(parse_int(context.data['nonce']), 0))
        signature = context.parameters.query['signature']
        stark_key = parse_int(context.data['stark_key'])
        if not verify(message_hash, signature[0], signature[1], stark_key):
            return web.HTTPUnauthorized()

        async with request.config_dict['async_session']() as session:
            from richmetas.models import Account
            try:
                account = (await session.execute(
                    select(Account).
                    where((Account.stark_key == Decimal(stark_key)) |
                          (Account.address == address)))).scalar_one_or_none()
                if not account:
                    account = Account(stark_key=stark_key)
                    session.add(account)
                if account.address is None:
                    account.address = address
            except MultipleResultsFound:
                return web.HTTPConflict()

            if account.stark_key != stark_key or account.address != address:
                return web.HTTPConflict()

            await session.commit()

        tx = await request.config_dict['richmetas']. \
            register_client(context.data['stark_key'],
                            context.data['address'],
                            context.data['nonce'],
                            signature)

        return web.json_response({'transaction_hash': tx})


@operations.register
async def get_client(request: Request):
    with openapi_context(request) as context:
        if context.parameters.query.get('cold'):
            stark_key = await request.config_dict['richmetas']. \
                get_client(context.parameters.path['address'])
            if stark_key == 0:
                return web.HTTPNotFound()

            return web.json_response({'stark_key': str(stark_key)})

        async with request.config_dict['async_session']() as session:
            from richmetas.models import Account

            try:
                address = utils.to_checksum_address(context.parameters.path['address'])
                account = (await session.execute(
                    select(Account).
                    where(Account.address == address))).scalar_one()

                return web.json_response({'stark_key': '{:f}'.format(account.stark_key)})
            except NoResultFound:
                return web.HTTPNotFound()


@operations.register
async def create_blueprint(request: Request):
    with openapi_context(request) as context:
        minter = Decimal(context.data['minter'])
        if not authenticate(
                [context.data['permanent_id'].encode()],
                context.parameters.query['signature'],
                int(minter)):
            return web.HTTPUnauthorized()

        async with request.config_dict['async_session']() as session:
            from richmetas.models import Account, Blueprint, BlueprintSchema

            try:
                account = (await session.execute(
                    select(Account).
                    where(Account.stark_key == minter))).scalar_one()
            except NoResultFound:
                account = Account(stark_key=minter)
                session.add(account)

            try:
                blueprint = Blueprint(
                    permanent_id=context.data['permanent_id'],
                    minter=account,
                    expire_at=pendulum.now().add(days=7))
                session.add(blueprint)
                await session.commit()
            except IntegrityError:
                return web.HTTPBadRequest()

            return web.json_response(BlueprintSchema().dump(blueprint))


@operations.register
async def find_collections(request: Request):
    with openapi_context(request) as context:
        owner = context.parameters.query.get('owner')
        fungible = context.parameters.query.get('fungible')
        page = context.parameters.query.get('page', 1)
        size = context.parameters.query.get('size', 100)

    async with request.config_dict['async_session']() as session:
        from richmetas.models import TokenContract, TokenContractVerboseSchema, Account, Blueprint

        def augment(stmt):
            if owner:
                stmt = stmt.join(TokenContract.blueprint). \
                    join(Blueprint.minter). \
                    where(Account.address == owner)
            stmt = stmt. \
                where(TokenContract.fungible == (true() if fungible else false()))

            return stmt

        query = augment(select(TokenContract)). \
            order_by(desc(TokenContract.id)). \
            limit(size). \
            offset(size * (page - 1))
        count = augment(select(functions.count()).select_from(TokenContract))

        return web.json_response({
            'data': list(map(
                TokenContractVerboseSchema().dump,
                (await session.execute(
                    query.options(
                        selectinload(TokenContract.blueprint).
                        selectinload(Blueprint.minter)))).scalars())),
            'total': (await session.execute(count)).scalar_one(),
        })


@operations.register
async def register_collection(request: Request):
    with openapi_context(request) as context:
        async with request.config_dict['async_session']() as session:
            from richmetas.models import TokenContract, Account, Blueprint

            try:
                token_contract = (await session.execute(
                    select(TokenContract).
                    where(TokenContract.address == utils.to_checksum_address(context.data['address'])).
                    where(TokenContract.fungible == false()).
                    options(selectinload(TokenContract.blueprint).
                            selectinload(Blueprint.minter)))).scalar_one()
            except NoResultFound:
                token_contract = TokenContract(
                    address=context.data['address'],
                    fungible=False)
                session.add(token_contract)

            if 'blueprint' in context.data:
                blueprint = (await session.execute(
                    select(Blueprint).
                    where(Blueprint.permanent_id == context.data['blueprint']).
                    options(
                        selectinload(Blueprint.minter),
                        selectinload(Blueprint.contract)))).scalar_one()
                if blueprint.contract is not None and \
                        blueprint.contract != token_contract:
                    return web.HTTPBadRequest()
            else:
                minter = parse_int(context.data['minter'])
                try:
                    account = (await session.execute(
                        select(Account).
                        where(Account.stark_key == Decimal(minter)))).scalar_one()
                except NoResultFound:
                    account = Account(stark_key=minter)
                    session.add(account)

                blueprint = Blueprint(minter=account)
                session.add(blueprint)

            if token_contract.blueprint is not None and \
                    token_contract.blueprint.minter != blueprint.minter:
                return web.HTTPForbidden()

            if not authenticate(
                    [context.data['address'],
                     context.data['name'].encode(),
                     context.data['symbol'].encode(),
                     context.data['base_uri'].encode(),
                     context.data['image'].encode(),
                     context.data.get('background_image', '').encode(),
                     context.data.get('description', '').encode()],
                    context.parameters.query['signature'],
                    int(blueprint.minter.stark_key)):
                return web.HTTPUnauthorized()

            token_contract.blueprint = blueprint
            token_contract.name = context.data['name']
            token_contract.symbol = context.data['symbol']
            token_contract.base_uri = context.data['base_uri']
            token_contract.image = context.data['image']
            token_contract.background_image = context.data.get('background_image')
            token_contract.description = context.data.get('description')

            await session.commit()
            req, signature = request.config_dict['forwarder'].forward(
                *request.config_dict['ether_richmetas'].register_contract(
                    token_contract.address, ContractKind.ERC721, int(blueprint.minter.stark_key)))

            return web.json_response({
                'req': ReqSchema().dump(req),
                'signature': signature,
            })


@operations.register
async def get_collection(request: Request):
    with openapi_context(request) as context:
        address = Web3.toChecksumAddress(context.parameters.path.address)
        async with request.config_dict['async_session']() as session:
            from richmetas.models import TokenContract, TokenContractVerboseSchema, Blueprint

            try:
                token_contract = (await session.execute(
                    select(TokenContract).
                    where(TokenContract.address == address).
                    options(
                        selectinload(TokenContract.blueprint).
                        selectinload(Blueprint.minter)))).scalar_one()

                return web.json_response(TokenContractVerboseSchema().dump(token_contract))
            except NoResultFound:
                return web.HTTPNotFound()


@operations.register
async def get_metadata_by_permanent_id(request: Request):
    with openapi_context(request) as context:
        async with request.config_dict['async_session']() as session:
            from richmetas.models import Token, TokenContract, Blueprint

            try:
                token = (await session.execute(
                    select(Token).
                    join(Token.contract).
                    join(TokenContract.blueprint).
                    where(Token.token_id == parse_int(context.parameters.path['token_id'])).
                    where(Blueprint.permanent_id == context.parameters.path['permanent_id']))).scalar_one()

                return web.json_response(token.asset_metadata)
            except NoResultFound:
                return web.HTTPNotFound()


@operations.register
async def get_metadata(request: Request):
    with openapi_context(request) as context:
        token_id = parse_int(context.parameters.path['token_id'])
        address = Web3.toChecksumAddress(context.parameters.path['address'])
        async with request.config_dict['async_session']() as session:
            from richmetas.models import TokenContract, Token

            try:
                token = (await session.execute(
                    select(Token).
                    join(Token.contract).
                    where(Token.token_id == token_id).
                    where(TokenContract.address == address))).scalar_one()

                return web.json_response(token.asset_metadata)
            except NoResultFound:
                return web.HTTPNotFound()


@operations.register
async def update_metadata(request: Request):
    with openapi_context(request) as context:
        token_id = parse_int(request.match_info['token_id'])
        address = Web3.toChecksumAddress(context.parameters.path['address'])
        async with request.config_dict['async_session']() as session:
            from richmetas.models import TokenContract, Blueprint, Token, TokenSchema

            try:
                token_contract = (await session.execute(
                    select(TokenContract).
                    where(TokenContract.address == address).
                    where(TokenContract.blueprint != null()).
                    options(
                        selectinload(TokenContract.blueprint).
                        selectinload(Blueprint.minter)))).scalar_one()
            except NoResultFound:
                return web.HTTPNotFound()

            try:
                token = (await session.execute(
                    select(Token).
                    where(Token.token_id == token_id).
                    where(Token.contract == token_contract).
                    options(selectinload(Token.contract)))).scalar_one()
            except NoResultFound:
                token = Token(contract=token_contract, token_id=token_id, nonce=0)
                session.add(token)

            if not authenticate(
                    [token_contract.address, token_id, token.nonce],
                    context.parameters.query['signature'],
                    int(token_contract.blueprint.minter.stark_key)):
                return web.HTTPUnauthorized()

            token.name = context.data['name']
            token.description = context.data['description']
            token.image = context.data['image']
            token.asset_metadata = pyrsistent.thaw(context.data)
            token.nonce += 1

            await session.commit()

            return web.json_response(TokenSchema().dump(token))


@operations.register
async def find_tokens(request: Request):
    with openapi_context(request) as context:
        q = context.parameters.query.get('q')
        owner = context.parameters.query.get('owner')
        collection = context.parameters.query.get('collection')
        sort = context.parameters.query.get('sort')
        asc = context.parameters.query.get('asc')
        page = context.parameters.query.get('page', 1)
        size = context.parameters.query.get('size', 100)

    async with request.config_dict['async_session']() as session:
        from richmetas.models import Token, TokenVerboseSchema, TokenContract, Account, LimitOrder

        def augment(stmt):
            if q:
                stmt = stmt. \
                    where(Token.name.ilike(f'%{q}%'))
            if owner:
                stmt = stmt.join(Token.owner). \
                    where(Account.address == Web3.toChecksumAddress(owner))
            if collection:
                stmt = stmt.join(Token.contract). \
                    where(TokenContract.address == Web3.toChecksumAddress(collection))

            return stmt

        so = dict(token_id=Token.token_id, name=Token.name).get(sort, Token.id)
        query = augment(select(Token)). \
            order_by(so if asc else desc(so)). \
            limit(size). \
            offset(size * (page - 1))
        count = augment(select(functions.count()).select_from(Token))

        return web.json_response({
            'data': list(map(
                TokenVerboseSchema().dump,
                (await session.execute(
                    query.options(
                        selectinload(Token.contract),
                        selectinload(Token.owner),
                        selectinload(Token.ask).
                        selectinload(LimitOrder.quote_contract)
                    ))).scalars())),
            'total': (await session.execute(count)).scalar_one(),
        })


@operations.register
async def get_token(request: Request):
    with openapi_context(request) as context:
        token_id = parse_int(context.parameters.path['token_id'])
        address = Web3.toChecksumAddress(context.parameters.path['address'])
        async with request.config_dict['async_session']() as session:
            from richmetas.models import Token, TokenVerboseSchema, TokenContract, LimitOrder

            try:
                token = (await session.execute(
                    select(Token).
                    join(Token.contract).
                    where(Token.token_id == token_id).
                    where(TokenContract.address == address).
                    options(
                        selectinload(Token.contract),
                        selectinload(Token.owner),
                        selectinload(Token.ask).
                        selectinload(LimitOrder.quote_contract)))).scalar_one()

                return web.json_response(TokenVerboseSchema().dump(token))
            except NoResultFound:
                return web.HTTPNotFound()


@operations.register
async def get_balance(request: Request):
    with openapi_context(request) as context:
        if context.parameters.query.get('cold'):
            balance = await request.config_dict['richmetas'].get_balance(
                context.parameters.query['user'],
                context.parameters.query['contract'])

            return web.json_response({'balance': str(balance)})

        async with request.config_dict['async_session']() as session:
            from richmetas.models import Balance, Account, TokenContract

            try:
                balance = (await session.execute(
                    select(Balance).
                    join(Balance.account).
                    join(Balance.contract).
                    where(Account.stark_key == Decimal(context.parameters.query['user'])).
                    where(TokenContract.address == utils.to_checksum_address(context.parameters.query['contract'])))).scalar_one()

                return web.json_response({'balance': '{:f}'.format(balance.amount)})
            except NoResultFound:
                return web.json_response({'balance': str(0)})


@operations.register
async def get_owner(request: Request):
    with openapi_context(request) as context:
        owner = await request.config_dict['richmetas'].get_owner(
            context.parameters.query['token_id'],
            context.parameters.query['contract'])

        return web.json_response({'owner': str(owner)})


@operations.register
async def mint(request: Request):
    with openapi_context(request) as context:
        tx = await request.config_dict['richmetas'].mint(
            context.data['user'],
            context.data['token_id'],
            context.data['contract'],
            context.data['nonce'],
            context.parameters.query['signature'])

        return web.json_response({'transaction_hash': tx})


@operations.register
async def withdraw(request: Request):
    with openapi_context(request) as context:
        tx = await request.config_dict['richmetas'].withdraw(
            context.data['user'],
            context.data['amount_or_token_id'],
            context.data['contract'],
            context.data['address'],
            context.data['nonce'],
            context.parameters.query['signature'])

        return web.json_response({'transaction_hash': tx})


@operations.register
async def transfer(request: Request):
    async with request.config_dict['async_session']() as session:
        from richmetas.models import TokenContract, Transfer

        with openapi_context(request) as context:
            try:
                token_contract = (await session.execute(
                    select(TokenContract).
                    where(TokenContract.address == utils.to_checksum_address(context.data['contract'])))).scalar_one()
            except NoResultFound:
                return web.HTTPBadRequest()

            if not token_contract.fungible:
                tx = request.config_dict['richmetas'].transfer(
                    context.data['from'],
                    context.data['to'],
                    context.data['amount_or_token_id'],
                    context.data['contract'],
                    context.data['nonce'],
                    context.parameters.query['signature'])

                return web.json_response({'transaction_hash': tx})

            tx = request.config_dict['richmetas']._invoke(
                'transfer',
                [
                    context.data['from'],
                    context.data['to'],
                    context.data['amount_or_token_id'],
                    context.data['contract'],
                    context.data['nonce'],
                ],
                context.parameters.query['signature']
            )

        message_hash = functools.reduce(lambda x, y: pedersen_hash(y, x), reversed(tx.calldata[1:]), 0)
        if not verify(message_hash, tx.signature[0], tx.signature[1], tx.calldata[0]):
            return web.HTTPUnauthorized()

        hash_ = '0x%x' % tx.calculate_hash(request.config_dict['starknet_general_config'])
        tr = (await session.execute(select(Transfer).where(Transfer.hash == hash_))).scalar_one_or_none()
        if tr:
            if tr.status == Status.REJECTED.value:
                return web.HTTPConflict()
        else:
            await TransferService(session).transfer(
                hash_, tx.calldata[0], tx.calldata[1], tx.calldata[2], token_contract, tx.calldata[4], tx.signature)
            await session.commit()
            await spawn(request, request.config_dict['gateway'].add_transaction(tx))

    return web.json_response({'transaction_hash': hash_})


@operations.register
async def find_deposits(request: Request):
    with openapi_context(request) as context:
        user = utils.to_checksum_address(context.parameters.query.get('user'))
        contract = context.parameters.query.get('contract')
        fungible = context.parameters.query.get('fungible')
        page = context.parameters.query.get('page', 1)
        size = context.parameters.query.get('size', 100)

    async with request.config_dict['async_session']() as session:
        from richmetas.models import Transaction, Deposit, DepositSchema, Balance, \
            TokenFlow, TokenFlowSchema, FlowType, TokenContract, Token, Account

        def augment(stmt):
            a1 = aliased(Account)
            a2 = aliased(Account)
            stmt = stmt. \
                join(Transaction.deposit, isouter=True). \
                join(Deposit.balance, isouter=True). \
                join(Balance.account.of_type(a1), isouter=True). \
                join(Transaction.token_flow, isouter=True). \
                join(TokenFlow.to_account.of_type(a2), isouter=True). \
                where((Deposit.id != null()) |
                      ((TokenFlow.id != null()) &
                       (TokenFlow.type == FlowType.DEPOSIT.value))). \
                where((a1.address == user) | (a2.address == user))
            if contract:
                address = utils.to_checksum_address(contract)
                c1 = aliased(TokenContract)
                c2 = aliased(TokenContract)
                stmt = stmt. \
                    join(Balance.contract.of_type(c1), isouter=True). \
                    join(TokenFlow.token, isouter=True). \
                    join(Token.contract.of_type(c2), isouter=True). \
                    where((c1.address == address) | (c2.address == address))
            if fungible is not None:
                stmt = stmt.where((Deposit.id if fungible else TokenFlow.id) != null())

            return stmt

        query = augment(select(Transaction)). \
            order_by(desc(Transaction.block_number)). \
            order_by(desc(Transaction.transaction_index)). \
            limit(size). \
            offset(size * (page - 1))
        count = augment(select(functions.count()).select_from(Transaction))

        return web.json_response({
            'data': [
                DepositSchema().dump(tx.deposit) if tx.deposit else
                TokenFlowSchema().dump(tx.token_flow) for tx in
                (await session.execute(
                    query.options(
                        selectinload(Transaction.block),
                        selectinload(Transaction.deposit).
                        selectinload(Deposit.balance).
                        selectinload(Balance.contract),
                        selectinload(Transaction.token_flow).
                        selectinload(TokenFlow.token).
                        selectinload(Token.contract)))).scalars()
            ],
            'total': (await session.execute(count)).scalar_one(),
        })


@operations.register
async def find_withdrawals(request: Request):
    with openapi_context(request) as context:
        user = utils.to_checksum_address(context.parameters.query.get('user'))
        contract = context.parameters.query.get('contract')
        fungible = context.parameters.query.get('fungible')
        page = context.parameters.query.get('page', 1)
        size = context.parameters.query.get('size', 100)

    async with request.config_dict['async_session']() as session:
        from richmetas.models import Transaction, Withdrawal, WithdrawalSchema, Balance, \
            TokenFlow, TokenFlowSchema, FlowType, TokenContract, Token, Account, EthEvent

        def augment(stmt):
            a1 = aliased(Account)
            a2 = aliased(Account)
            stmt = stmt. \
                join(Transaction.withdrawal, isouter=True). \
                join(Withdrawal.balance, isouter=True). \
                join(Balance.account.of_type(a1), isouter=True). \
                join(Transaction.token_flow, isouter=True). \
                join(TokenFlow.from_account.of_type(a2), isouter=True). \
                where((Withdrawal.id != null()) |
                      ((TokenFlow.id != null()) &
                       (TokenFlow.type == FlowType.WITHDRAWAL.value))). \
                where((a1.address == user) | (a2.address == user))
            if contract:
                address = utils.to_checksum_address(contract)
                c1 = aliased(TokenContract)
                c2 = aliased(TokenContract)
                stmt = stmt. \
                    join(Balance.contract.of_type(c1), isouter=True). \
                    join(TokenFlow.token, isouter=True). \
                    join(Token.contract.of_type(c2), isouter=True). \
                    where((c1.address == address) | (c2.address == address))
            if fungible is not None:
                stmt = stmt.where((Withdrawal.id if fungible else TokenFlow.id) != null())

            return stmt

        query = augment(select(Transaction)). \
            order_by(desc(Transaction.block_number)). \
            order_by(desc(Transaction.transaction_index)). \
            limit(size). \
            offset(size * (page - 1))
        count = augment(select(functions.count()).select_from(Transaction))

        return web.json_response({
            'data': [
                WithdrawalSchema().dump(tx.withdrawal) if tx.withdrawal else
                TokenFlowSchema().dump(tx.token_flow) for tx in
                (await session.execute(
                    query.options(
                        selectinload(Transaction.block),
                        selectinload(Transaction.withdrawal).
                        selectinload(Withdrawal.balance).
                        selectinload(Balance.contract),
                        selectinload(Transaction.withdrawal).
                        selectinload(Withdrawal.event).
                        selectinload(EthEvent.block),
                        selectinload(Transaction.token_flow).
                        selectinload(TokenFlow.token).
                        selectinload(Token.contract),
                        selectinload(Transaction.token_flow).
                        selectinload(TokenFlow.event).
                        selectinload(EthEvent.block)))).scalars()
            ],
            'total': (await session.execute(count)).scalar_one(),
        })


@operations.register
async def find_orders(request: Request):
    with openapi_context(request) as context:
        q = context.parameters.query.get('q')
        user = context.parameters.query.get('user')
        collection = context.parameters.query.get('collection')
        token_id = context.parameters.query.get('token_id')
        side = context.parameters.query.get('side')
        state = context.parameters.query.get('state')
        sort = context.parameters.query.get('sort')
        asc = context.parameters.query.get('asc')
        page = context.parameters.query.get('page', 1)
        size = context.parameters.query.get('size', 100)

    async with request.config_dict['async_session']() as session:
        from richmetas.models import LimitOrder, LimitOrderSchema, Account, Token, TokenContract, Transaction

        def augment(stmt):
            stmt = stmt.join(LimitOrder.token)
            if q:
                stmt = stmt.where(Token.name.ilike(f'%{q}%'))
            if user:
                stmt = stmt.join(LimitOrder.user). \
                    where(Account.address == user)
            if collection:
                stmt = stmt.join(Token.contract). \
                    where(TokenContract.address == collection)
            if token_id:
                stmt = stmt.where(Token.token_id == token_id)
            if side:
                stmt = stmt.where(LimitOrder.bid == (side == 'bid'))
            if state is not None:
                stmt = stmt.where(LimitOrder.fulfilled == [null(), true(), false()][state])

            return stmt

        query = augment(select(LimitOrder)). \
            limit(size). \
            offset(size * (page - 1))
        if sort == 'price':
            query = query.order_by(LimitOrder.quote_amount if asc else desc(LimitOrder.quote_amount))
        else:
            query = query.join(LimitOrder.tx). \
                order_by(Transaction.block_number if asc else desc(Transaction.block_number)). \
                order_by(Transaction.transaction_index if asc else desc(Transaction.transaction_index))

        count = augment(select(functions.count()).select_from(LimitOrder))

        return web.json_response({
            'data': list(map(
                LimitOrderSchema().dump,
                (await session.execute(
                    query.options(
                        selectinload(LimitOrder.user),
                        selectinload(LimitOrder.token).
                        selectinload(Token.contract).
                        selectinload(TokenContract.blueprint),
                        selectinload(LimitOrder.quote_contract).
                        selectinload(TokenContract.blueprint),
                        selectinload(LimitOrder.tx).
                        selectinload(Transaction.block)))).scalars())),
            'total': (await session.execute(count)).scalar_one(),
        })


@operations.register
async def create_order(request: Request):
    with openapi_context(request) as context:
        tx = await request.config_dict['richmetas'].create_order(
            context.data['order_id'],
            LimitOrder(**context.data.discard('order_id'), state=0),
            context.parameters.query['signature'])

        return web.json_response({'transaction_hash': tx})


@operations.register
async def get_order(request: Request):
    with openapi_context(request) as context:
        from richmetas.contracts import LimitOrderSchema

        limit_order = await request.config_dict['richmetas'].get_order(context.parameters.path['id'])
        if parse_int(limit_order.user) == 0:
            return web.HTTPNotFound()

        return web.json_response(LimitOrderSchema().dump(limit_order))


@operations.register
async def fulfill_order(request: Request):
    with openapi_context(request) as context:
        tx = await request.config_dict['richmetas'].fulfill_order(
            context.parameters.path['id'],
            context.data['user'],
            context.data['nonce'],
            context.parameters.query['signature'])

        return web.json_response({'transaction_hash': tx})


@operations.register
async def cancel_order(request: Request):
    with openapi_context(request) as context:
        tx = await request.config_dict['richmetas'].cancel_order(
            context.parameters.path['id'],
            context.parameters.query['nonce'],
            context.parameters.query['signature'])

        return web.json_response({'transaction_hash': tx})


@operations.register
async def get_tx_status(request: Request):
    status = await request.config_dict['feeder_gateway']. \
        get_transaction_status(tx_hash=request.match_info['hash'])
    if status['tx_status'] == Status.NOT_RECEIVED.value:
        return web.HTTPNotFound()

    return web.json_response(status)


@operations.register
async def inspect_tx(request: Request):
    from starkware.starknet.public.abi import get_selector_from_name

    tx = await request.config_dict['feeder_gateway']. \
        get_transaction(tx_hash=request.match_info['hash'])
    if tx['status'] == Status.NOT_RECEIVED.value or \
            parse_int(tx['transaction']['entry_point_selector']) != get_selector_from_name('transfer') or \
            tx['transaction']['entry_point_type'] != 'EXTERNAL':
        return web.HTTPNotFound()

    return web.json_response({
        'function': 'transfer',
        'inputs': dict(zip(
            ['from', 'to', 'amount_or_token_id', 'contract', 'nonce'],
            tx['transaction']['calldata'])),
        'status': tx['status'],
    })


async def upload(request: Request):
    import hashlib
    import mimetypes
    import aiohttp.hdrs

    reader = await request.multipart()
    part = await reader.next()
    if part.name != 'asset':
        return web.HTTPBadRequest()

    extension = mimetypes.guess_extension(part.headers[aiohttp.hdrs.CONTENT_TYPE])
    if not extension:
        return web.HTTPBadRequest()

    data = await part.read()
    asset = f'{hashlib.sha1(data).hexdigest()}{extension}'
    file = request.config_dict['bucket_root'] / asset[:2] / asset[2:4] / asset
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open('wb') as f:
        f.write(data)

    return web.json_response({'asset': asset})


def authenticate(message: list[Union[int, str, bytes]], signature: list[str], stark_key: int) -> bool:
    import hashlib

    message_hash = functools.reduce(
        lambda a, b: pedersen_hash(b, a),
        map(lambda x:
            parse_int(x) if not isinstance(x, bytes) else
            int.from_bytes(hashlib.sha1(x).digest(), byteorder='big'),
            reversed(message)), 0)
    r, s = map(parse_int, signature)

    return verify(message_hash, r, s, stark_key)


@click.command()
@click.option('--port', default=4000, type=int)
def serve(port: int):
    from pathlib import Path
    from .globals import async_session

    app = web.Application()
    w3 = Web3()
    app['ether_richmetas'] = EtherRichmetas(
        config('STARK_RICHMETAS_CONTRACT_ADDRESS', cast=parse_int), w3)
    app['forwarder'] = Forwarder(
        'RichmetasForwarder',
        '0.1.0',
        config('ETHER_FORWARDER_CONTRACT_ADDRESS'),
        config('ETHER_RICHMETAS_CONTRACT_ADDRESS'),
        Account.from_key(config('ETHER_PRIVATE_KEY')),
        w3)
    app['feeder_gateway'] = FeederGatewayClient(
        url=config('FEEDER_GATEWAY_URL'),
        retry_config=RetryConfig(n_retries=1))
    app['gateway'] = GatewayClient(
            url=config('GATEWAY_URL'),
            retry_config=RetryConfig(n_retries=1))
    app['richmetas'] = StarkRichmetas(
        config('STARK_RICHMETAS_CONTRACT_ADDRESS', cast=parse_int),
        app['feeder_gateway'],
        app['gateway'])
    app['starknet_general_config'] = StarknetGeneralConfig(
        chain_id={
            'mainnet': StarknetChainId.MAINNET,
            'testnet': StarknetChainId.TESTNET,
        }[config('STARK_NETWORK')])
    app['async_session'] = async_session

    app['bucket_root'] = Path(config('BUCKET_ROOT'))
    app.add_routes([web.post('/fs', upload),
                    web.static('/fs', app['bucket_root'])])

    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    schema = load(pkg_resources.resource_string(__name__, 'openapi.yaml'), Loader=Loader)
    setup_openapi(
        app,
        operations,
        schema=schema,
        spec=create_spec(schema),
        cors_middleware_kwargs=dict(allow_all=True))

    setup(app)

    web.run_app(app, port=port)

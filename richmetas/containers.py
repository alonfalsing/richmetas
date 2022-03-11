import logging
from pathlib import Path

from decouple import config
from dependency_injector import containers, providers
from eth_account import Account
from services.external_api.base_client import RetryConfig
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starkware.starknet.definitions.general_config import StarknetGeneralConfig, StarknetChainId
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient
from web3 import Web3

from richmetas.contracts import EtherRichmetas, Forwarder
from richmetas.contracts.starknet import Facade as StarkRichmetas
from richmetas.contracts.starknet.base import Base as BaseContract, BaseFeeder
from richmetas.sign import StarkKeyPair
from richmetas.utils import parse_int


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=['.serve', '.interpret', '.load'])
    config = providers.Configuration()

    engine = providers.Singleton(
        lambda database_url: create_async_engine(
            make_url(database_url).set(drivername='postgresql+asyncpg'),
            echo=False),
        config.database_url)
    async_session = providers.Singleton(
        sessionmaker,
        engine,
        expire_on_commit=False,
        class_=AsyncSession)
    w3 = providers.Singleton(Web3)

    feeder_gateway = providers.Factory(
        FeederGatewayClient,
        url=config.feeder_gateway_url,
        retry_config=RetryConfig(n_retries=1))
    gateway = providers.Factory(
        GatewayClient,
        url=config.gateway_url,
        retry_config=RetryConfig(n_retries=1))
    chain_id = providers.Singleton(
        {'mainnet': StarknetChainId.MAINNET, 'testnet': StarknetChainId.TESTNET}.get,
        config.stark_network)
    starknet_general_config = providers.Singleton(
        StarknetGeneralConfig,
        chain_id=chain_id)

    account = providers.Singleton(
        Account.from_key,
        config.ether_private_key)
    forwarder = providers.Factory(
        Forwarder,
        'RichmetasForwarder',
        '0.1.0',
        config.ether_forwarder_contract_address,
        config.ether_richmetas_contract_address,
        account,
        w3)
    ether_richmetas = providers.Factory(
        EtherRichmetas,
        config.ledger_address,
        w3)
    stark_key = providers.Singleton(
        StarkKeyPair,
        config.login_facade_admin_key)
    stark_richmetas = providers.Factory(
        StarkRichmetas,
        feeder_gateway,
        config.ledger_address,
        config.ledger_facade_address,
        config.exchange_address,
        config.exchange_facade_address,
        config.composer_address,
        config.composer_facade_address,
        config.login_address,
        config.login_facade_address,
        config.login_facade_admin_address,
        stark_key)
    ledger_contract = providers.Factory(BaseContract, config.ledger_address)
    exchange_contract = providers.Factory(BaseContract, config.exchange_address)
    composer_contract = providers.Factory(BaseContract, config.composer_address)
    legacy_ledger = providers.Factory(
        BaseFeeder,
        config.legacy_ledger_address,
        feeder_gateway)

    bucket_root = providers.Singleton(Path, config.bucket_root)


def build_container():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    container = Container()
    container.config.from_dict(dict([
        *map(lambda name: (name.lower(), config(name)), [
            'FEEDER_GATEWAY_URL',
            'GATEWAY_URL',
            'STARK_NETWORK',

            'ETHER_FORWARDER_CONTRACT_ADDRESS',
            'ETHER_RICHMETAS_CONTRACT_ADDRESS',
            'ETHER_PRIVATE_KEY',

            'DATABASE_URL',

            'BUCKET_ROOT',
        ]),

        *map(lambda name: (name.lower(), config(name, cast=parse_int)), [
            'LEDGER_ADDRESS',
            'LEDGER_FACADE_ADDRESS',
            'EXCHANGE_ADDRESS',
            'EXCHANGE_FACADE_ADDRESS',
            'COMPOSER_ADDRESS',
            'COMPOSER_FACADE_ADDRESS',
            'LOGIN_ADDRESS',
            'LOGIN_FACADE_ADDRESS',
            'LOGIN_FACADE_ADMIN_ADDRESS',
            'LOGIN_FACADE_ADMIN_KEY',

            'LEGACY_LEDGER_ADDRESS',
        ]),
    ]))

    return container

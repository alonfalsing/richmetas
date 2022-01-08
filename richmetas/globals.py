import logging

from decouple import config
from services.external_api.base_client import RetryConfig
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient
from starkware.starknet.services.api.gateway.gateway_client import GatewayClient

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
feeder_gateway_client = FeederGatewayClient(
    url=config('FEEDER_GATEWAY_URL'),
    retry_config=RetryConfig(n_retries=1))
gateway_client = GatewayClient(
    url=config('GATEWAY_URL'),
    retry_config=RetryConfig(n_retries=1))
engine = create_async_engine(
        make_url(config('DATABASE_URL')).set(drivername='postgresql+asyncpg'),
        echo=False,
    )
async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

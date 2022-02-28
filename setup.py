from setuptools import setup

setup(
    name='richmetas',
    version='0.0.1',
    packages=['richmetas'],
    package_data={
        'richmetas': ['openapi.yaml'],
        'richmetas.contracts': ['abi/*'],
    },
    install_requires=[
        'aiohttp',
        'aiohttp-sqlalchemy',
        'aiojobs',
        'asyncpg',
        'cairo-lang',
        'click',
        'dependency_injector',
        'ethereum',
        'jsonschema',
        'marshmallow',
        'pendulum',
        'py-eth-sig-utils',
        'python-decouple',
        'PyYAML',
        'rororo',
        'sqlalchemy',
    ],
    entry_points={
        'console_scripts': [
            'crawl = richmetas.crawl:crawl',
            'interpret = richmetas.interpret:cli',
            'serve = richmetas.serve:serve',
            'stark = richmetas.stark_key:cli',
            'ether_monitor = richmetas.ether_monitor:cli',
            'ddd = richmetas.ddd:cli',
        ],
    },
)

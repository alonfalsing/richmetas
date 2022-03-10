from starkware.starknet.services.api.feeder_gateway.feeder_gateway_client import FeederGatewayClient

from richmetas.sign import StarkKeyPair
from .composer import Composer, ComposerFacade
from .exchange import Exchange, ExchangeFacade
from .ledger import Ledger, LedgerFacade
from .login import Login, LoginFacadeAdmin


class Facade:
    def __init__(
            self,
            feeder: FeederGatewayClient,
            ledger_contract: int,
            ledger_facade_contract: int,
            exchange_contract: int,
            exchange_facade_contract: int,
            composer_contract: int,
            composer_facade_contract: int,
            login_contract: int,
            login_facade_contract: int,
            login_facade_admin_contract: int,
            login_facade_admin_key: StarkKeyPair):
        ledger_ = Ledger(ledger_contract, feeder)
        self.describe = ledger_.describe
        self.get_balance = ledger_.get_balance
        self.get_owner = ledger_.get_owner
        self.is_mint = ledger_.is_mint

        ledger_facade = LedgerFacade(ledger_facade_contract)
        self.withdraw = ledger_facade.withdraw
        self.transfer = ledger_facade.transfer
        self.mint = ledger_facade.mint

        exchange_ = Exchange(exchange_contract, feeder)
        self.get_order = exchange_.get_order

        exchange_facade = ExchangeFacade(exchange_facade_contract)
        self.create_order = exchange_facade.create_order
        self.fulfill_order = exchange_facade.fulfill_order
        self.cancel_order = exchange_facade.cancel_order

        composer_ = Composer(composer_contract, feeder)
        self.get_stereotype = composer_.get_stereotype
        self.get_token = composer_.get_token
        self.get_install = composer_.get_install

        composer_facade = ComposerFacade(composer_facade_contract)
        self.create_stereotype = composer_facade.create_stereotype
        self.add_token = composer_facade.add_token
        self.remove_token = composer_facade.remove_token
        self.activate_stereotype = composer_facade.activate_stereotype
        self.install_token = composer_facade.install_token
        self.uninstall_token = composer_facade.uninstall_token
        self.execute_stereotype = composer_facade.execute_stereotype
        self.launch_stereotype = composer_facade.launch_stereotype
        self.solve_stereotype = composer_facade.solve_stereotype

        login_ = Login(login_contract, feeder)
        self.get_account = login_.get_account

        login_facade_admin = LoginFacadeAdmin(
            login_facade_admin_contract, login_facade_contract, login_facade_admin_key)
        self.register_account = login_facade_admin.register_account

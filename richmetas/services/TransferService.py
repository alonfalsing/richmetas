from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from richmetas.models import Account, Balance, TokenContract, Transfer
from richmetas.utils import Status


class TransferService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def transfer(
            self,
            hash_: str,
            from_: int,
            to_: int,
            amount: int,
            contract: TokenContract,
            nonce: int,
            signature: Optional[list[int]] = None,
            status: str = Status.NOT_RECEIVED.value):
        from_account = await self.lift_account(from_)
        to_account = await self.lift_account(to_)
        transfer = Transfer(
            hash=hash_,
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            contract=contract,
            nonce=nonce,
            signature_r=signature and signature[0],
            signature_s=signature and signature[1],
            status=status)
        self._session.add(transfer)

        from_balance = await self.lift_balance(from_account, contract)
        to_balance = await self.lift_balance(to_account, contract)
        from_balance.amount -= amount
        to_balance.amount += amount

    async def reject(self, transfer: Transfer):
        transfer.status = Status.REJECTED.value

        from_balance = await self.lift_balance(transfer.from_account, transfer.contract)
        to_balance = await self.lift_balance(transfer.to_account, transfer.contract)
        from_balance.amount += transfer.amount
        to_balance.amount -= transfer.amount

    async def lift_balance(self, account: Account, contract: TokenContract):
        try:
            balance = (await self._session.execute(
                select(Balance).
                where(Balance.account == account).
                where(Balance.contract == contract))).scalar_one()
        except NoResultFound:
            balance = Balance(account=account, contract=contract, amount=0)
            self._session.add(balance)

        return balance

    async def lift_account(self, stark_key: int):
        try:
            account = (await self._session.execute(
                select(Account).
                where(Account.stark_key == Decimal(stark_key)))).scalar_one()
        except NoResultFound:
            account = Account(stark_key=stark_key)
            self._session.add(account)

        return account

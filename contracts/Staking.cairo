%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_nn, assert_not_zero, unsigned_div_rem
from starkware.starknet.common.syscalls import get_block_timestamp, get_contract_address
from acl import get_access, toggle_access, acl_secure
from admin import get_admin, change_admin
from LedgerInterface import LedgerInterface, ContractDescription, KIND_ERC20, KIND_ERC721
from StakingInterface import Revenue, Staking

const INTEREST_SCALE = 10 ** 6

@storage_var
func _ledger() -> (address : felt):
end

@storage_var
func _revenue(contract : felt) -> (revenue : Revenue):
end

@storage_var
func _staking(id : felt) -> (staking : Staking):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ledger : felt, admin : felt):
    initialize(ledger)
    change_admin(admin)

    return ()
end

@external
func initialize{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ledger : felt):
    let (address) = _ledger.read()
    if address != 0:
        return ()
    end

    _ledger.write(ledger)
    return ()
end

@view
func get_ledger{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        address : felt):
    return _ledger.read()
end

@view
func get_revenue{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt) -> (
        revenue : Revenue):
    return _revenue.read(contract=contract)
end

@external
func set_revenue{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, interest_or_amount : felt, revenue_contract : felt, faucet : felt):
    acl_secure()

    let (ledger) = _ledger.read()
    let (desc) = LedgerInterface.describe(contract_address=ledger, contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0
    assert_nn(interest_or_amount)
    let (desc) = LedgerInterface.describe(contract_address=ledger, contract=revenue_contract)
    assert desc.kind = KIND_ERC20
    assert_not_zero(faucet)

    _revenue.write(contract, Revenue(
        interest_or_amount=interest_or_amount,
        contract=revenue_contract,
        faucet=faucet))

    return ()
end

@view
func get_staking{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt) -> (
        staking : Staking):
    return _staking.read(id=id)
end

@external
func stake{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt, amount_or_token_id : felt, contract : felt):
    alloc_locals
    acl_secure()

    let (staking) = _staking.read(id=id)
    assert staking.started_at = 0
    let (revenue) = _revenue.read(contract=contract)
    assert_not_zero(revenue.contract)

    let (ledger) = _ledger.read()
    let (this) = get_contract_address()
    LedgerInterface.transfer(
        contract_address=ledger,
        from_=user,
        to_=this,
        amount_or_token_id=amount_or_token_id,
        contract=contract)

    let (timestamp) = get_block_timestamp()
    _staking.write(id, Staking(
        user=user,
        amount_or_token_id=amount_or_token_id,
        contract=contract,
        started_at=timestamp,
        ended_at=0))

    return ()
end

@external
func unstake{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt):
    alloc_locals
    acl_secure()

    let (staking) = _staking.read(id=id)
    assert_not_zero(staking.started_at)
    assert staking.ended_at = 0

    let (timestamp) = get_block_timestamp()
    let seconds = timestamp - staking.started_at
    assert_nn(seconds)
    _staking.write(id, Staking(
        user=staking.user,
        amount_or_token_id=staking.amount_or_token_id,
        contract=staking.contract,
        started_at=staking.started_at,
        ended_at=timestamp))

    let (ledger) = _ledger.read()
    let (desc) = LedgerInterface.describe(contract_address=ledger, contract=staking.contract)
    let (revenue) = _revenue.read(contract=staking.contract)
    let (q, _) = unsigned_div_rem(seconds, 24 * 60 * 60)
    let (outputs) = calc_outputs(staking, revenue, desc.kind, q)
    assert_nn(outputs)

    let (this) = get_contract_address()
    LedgerInterface.transfer(
        contract_address=ledger,
        from_=this,
        to_=staking.user,
        amount_or_token_id=staking.amount_or_token_id,
        contract=staking.contract)
    LedgerInterface.transfer(
        contract_address=ledger,
        from_=revenue.faucet,
        to_=staking.user,
        amount_or_token_id=outputs,
        contract=revenue.contract)

    return ()
end

func calc_outputs{
        range_check_ptr}(
        staking : Staking, revenue : Revenue, kind : felt, days : felt) -> (
        amount : felt):
    if kind == KIND_ERC721:
        return (revenue.interest_or_amount * days)
    end

    if revenue.contract != staking.contract:
        let (q, _) = unsigned_div_rem(
            staking.amount_or_token_id * revenue.interest_or_amount * days,
            INTEREST_SCALE)

        return (q)
    end

    return calc_compound_outputs(staking.amount_or_token_id, revenue.interest_or_amount, days)
end

func calc_compound_outputs{
        range_check_ptr}(
        amount : felt, interest : felt, days : felt) -> (
        amount : felt):
    let new_amount = amount * INTEREST_SCALE
    assert_nn(new_amount)
    let interest = interest + INTEREST_SCALE
    assert_nn(interest)

    let (new_amount) = _calc_outputs(new_amount, interest, days)
    assert_nn(new_amount)

    let (q, _) = unsigned_div_rem(new_amount, INTEREST_SCALE)
    return (q - amount)
end

func _calc_outputs{
        range_check_ptr}(
        amount : felt, interest : felt, days : felt) -> (
        amount : felt):
    if days == 0:
        return (amount)
    end

    let amount = amount * interest
    assert_nn(amount)

    let (q, r) = unsigned_div_rem(amount, INTEREST_SCALE)
    return _calc_outputs(q, interest, days - 1)
end

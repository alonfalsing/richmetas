%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.starknet.common.syscalls import get_contract_address
from acl import get_access, toggle_access, acl_secure
from admin import get_admin, change_admin
from LedgerInterface import LedgerInterface, KIND_ERC20, KIND_ERC721
from ExchangeInterface import LimitOrder

const ASK = 0
const BID = 1

const STATE_NEW = 0
const STATE_FULFILLED = 1
const STATE_CANCELLED = 2

@storage_var
func _ledger() -> (address : felt):
end

@storage_var
func _order(id : felt) -> (order : LimitOrder):
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
func get_order{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt) -> (
        order : LimitOrder):
    return _order.read(id=id)
end

@external
func create_order{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt, bid : felt,
        base_contract : felt, base_token_id : felt,
        quote_contract : felt, quote_amount : felt):
    alloc_locals
    acl_secure()

    assert (bid - ASK) * (bid - BID) = 0
    assert_nn(quote_amount)

    let (order) = _order.read(id=id)
    assert order.user = 0

    let (ledger) = _ledger.read()
    let (desc) = LedgerInterface.describe(contract_address=ledger, contract=base_contract)
    assert desc.kind = KIND_ERC721
    let (desc) = LedgerInterface.describe(contract_address=ledger, contract=quote_contract)
    assert desc.kind = KIND_ERC20

    let (this) = get_contract_address()
    if bid == ASK:
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=user,
            to_=this,
            amount_or_token_id=base_token_id,
            contract=base_contract)
    else:
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=user,
            to_=this,
            amount_or_token_id=quote_amount,
            contract=quote_contract)
    end

    _order.write(id, LimitOrder(
        user=user,
        bid=bid,
        base_contract=base_contract,
        base_token_id=base_token_id,
        quote_contract=quote_contract,
        quote_amount=quote_amount,
        state=STATE_NEW))

    return ()
end

@external
func fulfill_order{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt):
    alloc_locals
    acl_secure()

    let (local order) = _order.read(id)
    assert_not_zero(order.user)
    assert order.state = STATE_NEW

    let (ledger) = _ledger.read()
    let (this) = get_contract_address()
    if order.bid == ASK:
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=user,
            to_=order.user,
            amount_or_token_id=order.quote_amount,
            contract=order.quote_contract)
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=this,
            to_=user,
            amount_or_token_id=order.base_token_id,
            contract=order.base_contract)
    else:
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=user,
            to_=order.user,
            amount_or_token_id=order.base_token_id,
            contract=order.base_contract)
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=this,
            to_=user,
            amount_or_token_id=order.quote_amount,
            contract=order.quote_contract)
    end

    _order.write(id, LimitOrder(
        user=order.user,
        bid=order.bid,
        base_contract=order.base_contract,
        base_token_id=order.base_token_id,
        quote_contract=order.quote_contract,
        quote_amount=order.quote_amount,
        state=STATE_FULFILLED))

    return ()
end

@external
func cancel_order{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt):
    alloc_locals
    acl_secure()

    let (local order) = _order.read(id)
    assert_not_zero(order.user)
    assert order.state = STATE_NEW

    let (ledger) = _ledger.read()
    let (this) = get_contract_address()
    if order.bid == ASK:
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=this,
            to_=order.user,
            amount_or_token_id=order.base_token_id,
            contract=order.base_contract)
    else:
        LedgerInterface.transfer(
            contract_address=ledger,
            from_=this,
            to_=order.user,
            amount_or_token_id=order.quote_amount,
            contract=order.quote_contract)
    end

    _order.write(id, LimitOrder(
        user=order.user,
        bid=order.bid,
        base_contract=order.base_contract,
        base_token_id=order.base_token_id,
        quote_contract=order.quote_contract,
        quote_amount=order.quote_amount,
        state=STATE_CANCELLED))

    return ()
end

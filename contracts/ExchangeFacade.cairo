%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from admin import get_admin, change_admin
from facade import get_underpinning, underpin_with
from lib import authenticate_r, authenticate_2r, authenticate_6r
from ExchangeInterface import ExchangeInterface

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt, admin : felt):
    underpin_with(underpinning)
    change_admin(admin)

    return ()
end

@external
func create_order{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt, bid : felt,
        base_contract : felt, base_token_id : felt,
        quote_contract : felt, quote_amount : felt):
    authenticate_6r(user, id, bid, base_contract, base_token_id, quote_contract, quote_amount)

    let (underpinning) = get_underpinning()
    ExchangeInterface.create_order(
        contract_address=underpinning,
        id=id,
        user=user,
        bid=bid,
        base_contract=base_contract,
        base_token_id=base_token_id,
        quote_contract=quote_contract,
        quote_amount=quote_amount)

    return ()
end

@external
func fulfill_order{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt, nonce : felt):
    authenticate_2r(user, id, nonce)

    let (underpinning) = get_underpinning()
    ExchangeInterface.fulfill_order(contract_address=underpinning, id=id, user=user)

    return ()
end

@external
func cancel_order{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, nonce : felt):
    alloc_locals
    let (local underpinning) = get_underpinning()
    let (order) = ExchangeInterface.get_order(contract_address=underpinning, id=id)

    let (__fp__, _) = get_fp_and_pc()
    authenticate_r(order.user, 2, &id)
    ExchangeInterface.cancel_order(contract_address=underpinning, id=id)

    return ()
end

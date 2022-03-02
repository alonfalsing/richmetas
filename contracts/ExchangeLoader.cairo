%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import assert_nn
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate
from loader import get_owner, change_owner
from ExchangeInterface import LimitOrder, ASK, BID, STATE_NEW, STATE_FULFILLED, STATE_CANCELLED

@storage_var
func _order(id : felt) -> (order : LimitOrder):
end

@constructor
func constructor{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt):
    change_owner(owner, 0)

    return ()
end

@external
func load_order{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt, bid : felt,
        base_contract : felt, base_token_id : felt,
        quote_contract : felt, quote_amount : felt, state : felt):
    assert (bid - ASK) * (bid - BID) = 0
    assert_nn(base_token_id)
    assert_nn(quote_amount)
    assert (state - STATE_NEW) * (state - STATE_FULFILLED) * (state - STATE_CANCELLED) = 0

    _order.write(id, LimitOrder(
        user=user,
        bid=bid,
        base_contract=base_contract,
        base_token_id=base_token_id,
        quote_contract=quote_contract,
        quote_amount=quote_amount,
        state=state))

    return ()
end

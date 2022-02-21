%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from admin import get_admin, change_admin
from facade import get_underpinning, underpin_with
from lib import authenticate_r
from LedgerInterface import LedgerInterface

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt, admin : felt):
    underpin_with(underpinning)
    change_admin(admin)

    return ()
end

@external
func withdraw{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, amount_or_token_id : felt, contract : felt, address : felt, nonce : felt):
    let (__fp__, _) = get_fp_and_pc()
    authenticate_r(user, 4, &amount_or_token_id)

    let (underpinning) = get_underpinning()
    LedgerInterface.withdraw(
        contract_address=underpinning,
        user=user,
        amount_or_token_id=amount_or_token_id,
        contract=contract,
        address=address,
        nonce=nonce)

    return ()
end

@external
func transfer{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to_ : felt, amount_or_token_id : felt, contract : felt, nonce : felt):
    let (__fp__, _) = get_fp_and_pc()
    authenticate_r(from_, 4, &to_)

    let (underpinning) = get_underpinning()
    LedgerInterface.transfer(
        contract_address=underpinning,
        from_=from_,
        to_=to_,
        amount_or_token_id=amount_or_token_id,
        contract=contract)

    return ()
end

@external
func mint{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, token_id : felt, contract : felt, nonce : felt):
    alloc_locals

    let (local underpinning) = get_underpinning()
    let (desc) = LedgerInterface.describe(contract_address=underpinning, contract=contract)

    let (__fp__, _) = get_fp_and_pc()
    authenticate_r(desc.mint, 4, &user)

    LedgerInterface.mint(
        contract_address=underpinning,
        user=user,
        token_id=token_id,
        contract=contract)

    return ()
end

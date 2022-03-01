%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import assert_nn
from starkware.cairo.common.registers import get_fp_and_pc
from admin import get_admin, change_admin
from lib import authenticate
from LedgerInterface import ContractDescription, KIND_ERC20, KIND_ERC721

@storage_var
func _description(contract : felt) -> (desc : ContractDescription):
end

@storage_var
func _balance(user : felt, contract : felt) -> (balance : felt):
end

@storage_var
func _owner(token_id : felt, contract : felt) -> (user : felt):
end

@storage_var
func _mint(token_id : felt, contract : felt) -> (mint : felt):
end

@external
func load_description{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, kind : felt, mint : felt, nonce : felt):
    assert (kind - KIND_ERC20) * (kind - KIND_ERC721) = 0
    let (admin) = get_admin()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(admin, 4, &contract)
    _description.write(contract, ContractDescription(
        kind=kind,
        mint=mint))

    return ()
end

@external
func load_balance{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, contract : felt, balance : felt, nonce : felt):
    assert_nn(balance)
    let (admin) = get_admin()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(admin, 4, &user)
    _balance.write(user=user, contract=contract, value=balance)

    return ()
end

@external
func load_owner{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        token_id : felt, contract : felt, owner : felt, mint : felt, nonce : felt):
    assert_nn(token_id)
    let (admin) = get_admin()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(admin, 5, &token_id)
    _owner.write(token_id=token_id, contract=contract, value=owner)
    if mint == 0:
        return ()
    end

    _mint.write(token_id=token_id, contract=contract, value=1)
    return ()
end

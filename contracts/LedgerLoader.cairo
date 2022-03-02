%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.math import assert_nn
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate
from LedgerInterface import ContractDescription, KIND_ERC20, KIND_ERC721

@storage_var
func _Loader_owner() -> (user : felt):
end

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

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt):
    _Loader_owner.write(owner)

    return ()
end

@view
func get_owner{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        user : felt):
    return _Loader_owner.read()
end

@external
func change_owner{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, nonce : felt):
    let (owner) = _Loader_owner.read()
    if owner == 0:
        _Loader_owner.write(user)
        return ()
    end

    let (__fp__, _) = get_fp_and_pc()
    authenticate(owner, 2, &user)

    _Loader_owner.write(user)
    return ()
end

@external
func load_description{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, kind : felt, mint : felt, nonce : felt):
    assert (kind - KIND_ERC20) * (kind - KIND_ERC721) = 0
    let (admin) = _Loader_owner.read()
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
    let (admin) = _Loader_owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(admin, 4, &user)
    _balance.write(user=user, contract=contract, value=balance)

    return ()
end

@external
func load_token{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        token_id : felt, contract : felt, owner : felt, mint : felt, nonce : felt):
    assert_nn(token_id)
    let (admin) = _Loader_owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(admin, 5, &token_id)
    _owner.write(token_id=token_id, contract=contract, value=owner)
    if mint == 0:
        return ()
    end

    _mint.write(token_id=token_id, contract=contract, value=1)
    return ()
end

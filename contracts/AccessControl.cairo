%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate

@contract_interface
namespace ACL:
    func change_admin(user : felt):
    end

    func toggle_access(contract : felt, allowed : felt):
    end
end

@storage_var
func _owner() -> (user : felt):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt):
    _owner.write(owner)

    return ()
end

@view
func owner{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        user : felt):
    return _owner.read()
end

@external
func change_owner{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 1, &user)
    _owner.write(user)

    return ()
end

@external
func acl_change_admin{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, user : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 2, &contract)
    ACL.change_admin(contract_address=contract, user=user)

    return ()
end

@external
func acl_toggle_access{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, friend_contract : felt, allowed : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 3, &contract)
    ACL.toggle_access(contract_address=contract, contract=friend_contract, allowed=allowed)

    return ()
end

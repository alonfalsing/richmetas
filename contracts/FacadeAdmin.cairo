%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate

@contract_interface
namespace Facade:
    func change_admin(user : felt):
    end

    func underpin_with(underpinning : felt):
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
func get_owner{
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
func facade_change_admin{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, user : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 2, &contract)
    Facade.change_admin(contract_address=contract, user=user)

    return ()
end

@external
func facade_underpin{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, underpinning : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 2, &contract)
    Facade.underpin_with(contract_address=contract, underpinning=underpinning)

    return ()
end

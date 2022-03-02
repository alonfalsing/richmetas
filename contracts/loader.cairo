%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate

@storage_var
func _Loader_owner() -> (user : felt):
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

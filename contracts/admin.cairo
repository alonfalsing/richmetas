%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address

@storage_var
func _admin() -> (admin : felt):
end

@view
func get_admin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        admin : felt):
    return _admin.read()
end

@external
func change_admin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user: felt):
    only_admin()
    _admin.write(user)

    return ()
end

func only_admin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    let (admin) = _admin.read()
    let (caller) = get_caller_address()
    assert admin * (caller - admin) = 0

    return ()
end

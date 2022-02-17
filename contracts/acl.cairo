%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from admin import only_admin

@storage_var
func _acl_access(contract : felt) -> (allowed : felt):
end

@view
func get_access{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt) -> (
        allowed : felt):
    return _acl_access.read(contract)
end

@external
func toggle_access{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, allowed : felt):
    assert allowed * (allowed - 1) = 0

    only_admin()
    _acl_access.write(contract=contract, value=allowed)

    return ()
end

func acl_secure{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    let (caller) = get_caller_address()
    let (allowed) = _acl_access.read(contract=caller)
    assert allowed = 1

    return ()
end

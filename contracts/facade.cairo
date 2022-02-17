%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import get_caller_address
from admin import only_admin

@storage_var
func _facade_underpinning() -> (address : felt):
end

@view
func get_underpinning{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        address : felt):
    return _facade_underpinning.read()
end

@external
func underpin_with{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt):
    only_admin()
    _facade_underpinning.write(underpinning)

    return ()
end

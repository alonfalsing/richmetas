%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from admin import get_admin, change_admin
from acl import get_access, toggle_access, acl_secure

@event
func register_account_event(stark_key : felt, ethereum_address : felt):
end

@storage_var
func _account(ethereum_address : felt) -> (stark_key : felt):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        admin : felt):
    change_admin(admin)

    return ()
end

@view
func get_account{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ethereum_address : felt) -> (
        stark_key : felt):
    return _account.read(ethereum_address)
end

@external
func register_account{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        stark_key : felt, ethereum_address : felt):
    acl_secure()
    _account.write(ethereum_address=ethereum_address, value=stark_key)
    register_account_event.emit(stark_key=stark_key, ethereum_address=ethereum_address)

    return ()
end

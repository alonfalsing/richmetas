%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from admin import get_admin, change_admin, only_admin
from facade import get_underpinning, underpin_with
from LoginInterface import LoginInterface

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt, admin : felt):
    underpin_with(underpinning)
    change_admin(admin)

    return ()
end

@external
func register_account{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        stark_key : felt, ethereum_address : felt):
    only_admin()

    let (underpinning) = get_underpinning()
    LoginInterface.register_account(
        contract_address=underpinning,
        stark_key=stark_key,
        ethereum_address=ethereum_address)

    return ()
end

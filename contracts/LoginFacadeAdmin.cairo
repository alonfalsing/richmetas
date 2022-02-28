%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate
from FacadeAdmin import constructor, get_owner, change_owner, facade_change_admin, facade_underpin
from LoginInterface import LoginInterface

@external
func register_account{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, stark_key : felt, ethereum_address : felt, nonce : felt):
    let (owner) = get_owner()
    let (__fp__, _) = get_fp_and_pc()
    authenticate(owner, 4, &contract)

    LoginInterface.register_account(
        contract_address=contract,
        stark_key=stark_key,
        ethereum_address=ethereum_address)
    return ()
end

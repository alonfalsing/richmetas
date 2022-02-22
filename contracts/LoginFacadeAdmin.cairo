%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from FacadeAdmin import constructor, get_owner, change_owner, facade_change_admin, facade_underpin
from StakingInterface import StakingInterface
from lib import authenticate_4r
from LoginInterface import LoginInterface

@external
func register_account{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, stark_key : felt, ethereum_address : felt, nonce : felt):
    let (owner) = get_owner()
    authenticate_4r(owner, contract, stark_key, ethereum_address, nonce)

    LoginInterface.register_account(
        contract_address=contract,
        stark_key=stark_key,
        ethereum_address=ethereum_address)
    return ()
end

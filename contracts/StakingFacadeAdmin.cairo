%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from FacadeAdmin import constructor, get_owner, change_owner, facade_change_admin, facade_underpin
from StakingInterface import StakingInterface
from lib import authenticate_6r

@external
func set_revenue{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        facade : felt, contract : felt, interest_or_amount : felt, revenue_contract : felt, faucet : felt, nonce : felt):
    let (owner) = get_owner()
    authenticate_6r(owner, facade, contract, interest_or_amount, revenue_contract, faucet, nonce)
    StakingInterface.set_revenue(
        contract_address=facade,
        contract=contract,
        interest_or_amount=interest_or_amount,
        revenue_contract=revenue_contract,
        faucet=faucet)

    return ()
end

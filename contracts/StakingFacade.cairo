%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from admin import get_admin, change_admin, only_admin
from facade import get_underpinning, underpin_with
from lib import authenticate_r, authenticate_3r
from StakingInterface import StakingInterface

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt, admin : felt):
    underpin_with(underpinning)
    change_admin(admin)

    return ()
end

@external
func set_revenue{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt, interest_or_amount : felt, revenue_contract : felt, faucet : felt):
    only_admin()

    let (underpinning) = get_underpinning()
    StakingInterface.set_revenue(
        contract_address=underpinning,
        contract=contract,
        interest_or_amount=interest_or_amount,
        revenue_contract=revenue_contract,
        faucet=faucet)

    return ()
end

@external
func stake{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, user : felt, amount_or_token_id : felt, contract : felt):
    authenticate_3r(user, id, amount_or_token_id, contract)

    let (underpinning) = get_underpinning()
    StakingInterface.stake(
        contract_address=underpinning,
        id=id,
        user=user,
        amount_or_token_id=amount_or_token_id,
        contract=contract)

    return ()
end

@external
func unstake{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, nonce : felt):
    alloc_locals
    let (local underpinning) = get_underpinning()
    let (staking) = StakingInterface.get_staking(contract_address=underpinning, id=id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate_r(staking.user, 2, &id)

    StakingInterface.unstake(contract_address=underpinning, id=id)

    return ()
end

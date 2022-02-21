%lang starknet

struct Revenue:
    member interest_or_amount : felt
    member contract : felt
    member faucet : felt
end

struct Staking:
    member user : felt
    member amount_or_token_id : felt
    member contract : felt
    member started_at : felt
    member ended_at : felt
end

@contract_interface
namespace StakingInterface:
    func set_revenue(contract : felt, interest_or_amount : felt, revenue_contract : felt, faucet : felt):
    end

    func get_staking(id : felt) -> (staking : Staking):
    end

    func stake(id : felt, user : felt, amount_or_token_id : felt, contract : felt):
    end

    func unstake(id : felt):
    end
end

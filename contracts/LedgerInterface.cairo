%lang starknet

const KIND_ERC20 = 1
const KIND_ERC721 = 2

struct ContractDescription:
    member kind : felt          # ERC20 / ERC721
    member mint : felt          # minter
end

@contract_interface
namespace LedgerInterface:
    func describe(contract : felt) -> (desc : ContractDescription):
    end

    func get_owner(token_id : felt, contract : felt) -> (user : felt):
    end

    func withdraw(user : felt, amount_or_token_id : felt, contract : felt, address : felt, nonce: felt):
    end

    func transfer(from_ : felt, to_ : felt, amount_or_token_id : felt, contract : felt):
    end

    func mint(user : felt, token_id : felt, contract : felt):
    end
end

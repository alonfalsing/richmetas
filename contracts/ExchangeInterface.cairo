%lang starknet

const ASK = 0
const BID = 1

const STATE_NEW = 0
const STATE_FULFILLED = 1
const STATE_CANCELLED = 2

struct LimitOrder:
    member user : felt
    member bid : felt
    member base_contract : felt
    member base_token_id : felt
    member quote_contract : felt
    member quote_amount : felt
    member state : felt
end

@contract_interface
namespace ExchangeInterface:
    func get_order(id : felt) -> (order : LimitOrder):
    end

    func create_order(
            id : felt, user : felt, bid : felt,
            base_contract : felt, base_token_id : felt,
            quote_contract : felt, quote_amount : felt):
    end

    func fulfill_order(id : felt, user : felt):
    end

    func cancel_order(id : felt):
    end
end

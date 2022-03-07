%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.starknet.common.messages import send_message_to_l1
from admin import get_admin, change_admin
from acl import get_access, toggle_access, acl_secure
from LedgerInterface import ContractDescription, KIND_ERC20, KIND_ERC721

const WITHDRAW = 0

@storage_var
func _l1_contract() -> (address : felt):
end

@storage_var
func _description(contract : felt) -> (desc : ContractDescription):
end

@storage_var
func _balance(user : felt, contract : felt) -> (balance : felt):
end

@storage_var
func _owner(token_id : felt, contract : felt) -> (user : felt):
end

@storage_var
func _mint(token_id : felt, contract : felt) -> (mint : felt):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        l1_contract : felt, admin : felt):
    initialize(l1_contract)
    change_admin(admin)

    return ()
end

@external
func initialize{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        l1_contract : felt):
    let (address) = _l1_contract.read()
    if address != 0:
        return ()
    end

    _l1_contract.write(value=l1_contract)
    _description.write(0, ContractDescription(
        kind=KIND_ERC20,
        mint=0))

    return ()
end

@view
func describe{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        contract : felt) -> (
        desc : ContractDescription):
    return _description.read(contract=contract)
end

@view
func get_balance{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, contract : felt) -> (
        balance : felt):
    return _balance.read(user=user, contract=contract)
end

@view
func get_owner{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        token_id : felt, contract : felt) -> (
        user : felt):
    return _owner.read(token_id=token_id, contract=contract)
end

@view
func is_mint{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        token_id : felt, contract : felt) -> (
        mint : felt):
    return _mint.read(token_id=token_id, contract=contract)
end

@l1_handler
func register_contract{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_address : felt, contract : felt, kind : felt, mint : felt):
    assert (kind - KIND_ERC20) * (kind - KIND_ERC721) = 0

    let (l1_contract) = _l1_contract.read()
    assert from_address = l1_contract

    let (desc) = _description.read(contract=contract)
    assert desc.kind = 0

    _description.write(contract, ContractDescription(
        kind=kind,
        mint=mint))

    return ()
end

@l1_handler
func deposit{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_address : felt, user : felt, amount_or_token_id : felt, contract : felt, nonce : felt):
    let (l1_contract) = _l1_contract.read()
    assert from_address = l1_contract

    let (desc) = _description.read(contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0

    if desc.kind == KIND_ERC20:
        let (balance) = _balance.read(user=user, contract=contract)
        let new_balance = balance + amount_or_token_id
        assert_nn(new_balance)

        _balance.write(user, contract, new_balance)
    else:
        let (owner) = _owner.read(token_id=amount_or_token_id, contract=contract)
        assert owner = 0

        _owner.write(amount_or_token_id, contract, user)
    end

    return ()
end

@external
func withdraw{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, amount_or_token_id : felt, contract : felt, address : felt, nonce : felt):
    alloc_locals
    acl_secure()
    assert_nn(amount_or_token_id)

    let (desc) = _description.read(contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0

    let (local mint) = _mint.read(amount_or_token_id, contract)
    if desc.kind == KIND_ERC20:
        let (balance) = _balance.read(user=user, contract=contract)
        let new_balance = balance - amount_or_token_id
        assert_nn(new_balance)

        _balance.write(user, contract, new_balance)
    else:
        let (owner) = _owner.read(token_id=amount_or_token_id, contract=contract)
        assert user = owner

        _owner.write(amount_or_token_id, contract, 0)
        _mint.write(amount_or_token_id, contract, 0)
    end

    let (l1_contract) = _l1_contract.read()
    let (payload : felt*) = alloc()
    assert payload[0] = WITHDRAW
    assert payload[1] = address
    assert payload[2] = amount_or_token_id
    assert payload[3] = contract
    assert payload[4] = mint
    assert payload[5] = nonce
    send_message_to_l1(
        to_address=l1_contract,
        payload_size=6,
        payload=payload)

    return ()
end

@external
func transfer{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        from_ : felt, to_ : felt, amount_or_token_id : felt, contract : felt):
    acl_secure()
    assert_nn(amount_or_token_id)
    assert_not_zero(from_)

    let (desc) = _description.read(contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0

    if desc.kind == KIND_ERC20:
        let (balance) = _balance.read(user=from_, contract=contract)
        let new_balance = balance - amount_or_token_id
        assert_nn(new_balance)
        _balance.write(from_, contract, new_balance)

        let (balance) = _balance.read(user=to_, contract=contract)
        let new_balance = balance + amount_or_token_id
        assert_nn(new_balance)
        _balance.write(to_, contract, new_balance)
    else:
        let (owner) = _owner.read(token_id=amount_or_token_id, contract=contract)
        assert from_ = owner

        _owner.write(amount_or_token_id, contract, to_)
    end

    return ()
end

@external
func mint{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, token_id : felt, contract : felt):
    acl_secure()
    assert_nn(token_id)

    let (desc) = _description.read(contract=contract)
    assert desc.kind = KIND_ERC721

    let (owner) = _owner.read(token_id, contract)
    assert owner = 0

    _owner.write(token_id, contract, user)
    _mint.write(token_id, contract, 1)

    return ()
end

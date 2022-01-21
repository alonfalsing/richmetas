%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import (HashBuiltin, SignatureBuiltin)
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.math import assert_nn, assert_not_zero
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.starknet.common.messages import send_message_to_l1
from starkware.starknet.common.syscalls import get_caller_address, get_tx_signature

const KIND_ERC20 = 1
const KIND_ERC721 = 2
const WITHDRAW = 0

const ASK = 0
const BID = 1

const STATE_NEW = 0
const STATE_FULFILLED = 1
const STATE_CANCELLED = 2

struct ContractDescription:
    member kind : felt          # ERC20 / ERC721
    member mint : felt          # minter
end

struct LimitOrder:
    member user : felt
    member bid : felt
    member base_contract : felt
    member base_token_id : felt
    member quote_contract : felt
    member quote_amount : felt
    member state : felt
end

@storage_var
func l1_contract_address() -> (address : felt):
end

@storage_var
func admin() -> (adm : felt):
end

@storage_var
func pause() -> (paus : felt):
end

@storage_var
func description(contract : felt) -> (desc : ContractDescription):
end

@storage_var
func client(address : felt) -> (usr : felt):
end

@storage_var
func balance(user : felt, contract : felt) -> (bal : felt):
end

@storage_var
func owner(token_id : felt, contract : felt) -> (usr : felt):
end

@storage_var
func origin(token_id : felt, contract : felt) -> (org : felt):
end

@storage_var
func order(id : felt) -> (ord : LimitOrder):
end

@constructor
func constructor{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    l1_caddr: felt,
    adm : felt):
    l1_contract_address.write(value=l1_caddr)
    admin.write(value=adm)

    description.write(0, ContractDescription(
        kind=KIND_ERC20,
        mint=0))

    return ()
end

@view
func get_admin{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}() -> (
    adm : felt):
    return admin.read()
end

@view
func is_pause{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}() -> (
    paus : felt):
    return pause.read()
end

@view
func describe{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    contract : felt) -> (
    desc : ContractDescription):
    return description.read(contract=contract)
end

@view
func get_client{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    address : felt) -> (
    usr : felt):
    return client.read(address=address)
end

@view
func get_balance{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    contract : felt) -> (
    bal : felt):
    return balance.read(user=user, contract=contract)
end

@view
func get_owner{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    token_id : felt,
    contract : felt) -> (
    usr : felt):
    return owner.read(token_id=token_id, contract=contract)
end

@view
func get_origin{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    token_id : felt,
    contract : felt) -> (
    org : felt):
    return origin.read(token_id=token_id, contract=contract)
end

@view
func get_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt) -> (
    ord : LimitOrder):
    return order.read(id=id)
end

@external
func set_admin{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    adm : felt,
    nonce : felt):
    alloc_locals

    let (adm) = admin.read()
    let inputs : felt* = alloc()
    inputs[0] = adm
    inputs[1] = nonce
    verify_inputs_by_signature(adm, 2, inputs)

    admin.write(adm)

    return ()
end

@external
func ac_set_admin{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    adm : felt):
    let (caller) = get_caller_address()
    let (old) = admin.read()
    assert caller = old

    admin.write(adm)

    return()
end

@external
func set_pause{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    paus_ : felt,
    nonce : felt):
    alloc_locals

    let (adm) = admin.read()
    let inputs : felt* = alloc()
    inputs[0] = paus_
    inputs[1] = nonce
    verify_inputs_by_signature(adm, 2, inputs)

    _set_pause(paus_)

    return ()
end

@external
func ac_set_pause{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    paus_ : felt):
    let (caller) = get_caller_address()
    let (adm) = admin.read()
    assert caller = adm

    return _set_pause(paus_)
end

func _set_pause{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    paus_ : felt):
    assert paus_ * (paus_ - 1) = 0
    pause.write(paus_)

    return ()
end

@l1_handler
func register_contract{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    from_address : felt,
    contract : felt,
    kind : felt,
    mint : felt):
    check_on()
    assert (kind - KIND_ERC20) * (kind - KIND_ERC721) = 0

    let (l1_caddr) = l1_contract_address.read()
    assert l1_caddr = from_address

    let (desc) = description.read(contract=contract)
    assert desc.kind = 0

    description.write(contract, ContractDescription(
        kind=kind,
        mint=mint))

    return ()
end

@external
func register_client{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    address : felt,
    nonce : felt):
    check_on()

    let (usr) = client.read(address=address)
    assert usr = 0

    let inputs : felt* = alloc()
    inputs[0] = address
    inputs[1] = nonce
    verify_inputs_by_signature(user, 2, inputs)

    client.write(address, user)

    return ()
end

@external
func mint{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    token_id : felt,
    contract : felt,
    nonce : felt):
    alloc_locals

    let (desc) = description.read(contract=contract)
    let inputs : felt* = alloc()
    inputs[0] = user
    inputs[1] = token_id
    inputs[2] = contract
    inputs[3] = nonce
    verify_inputs_by_signature(desc.mint, 4, inputs)

    local ecdsa_ptr : SignatureBuiltin* = ecdsa_ptr
    _mint(user, token_id, contract)

    return ()
end

@external
func ac_mint{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    token_id : felt,
    contract : felt):
    let (caller) = get_caller_address()
    let (desc) = description.read(contract=contract)
    assert caller = desc.mint

    return _mint(user, token_id, contract)
end

func _mint{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    token_id : felt,
    contract : felt):
    check_on()
    assert_nn(token_id)

    let (desc) = description.read(contract=contract)
    assert desc.kind = KIND_ERC721

    let (usr) = owner.read(token_id, contract)
    assert usr = 0

    owner.write(token_id, contract, user)
    origin.write(token_id, contract, 1)

    return ()
end

@external
func withdraw{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    amount_or_token_id : felt,
    contract : felt,
    address : felt,
    nonce : felt):
    alloc_locals

    let inputs : felt* = alloc()
    inputs[0] = amount_or_token_id
    inputs[1] = contract
    inputs[2] = address
    inputs[3] = nonce
    verify_inputs_by_signature(user, 4, inputs)

    let ecdsa_ptr = ecdsa_ptr
    _withdraw(user, amount_or_token_id, contract, address, nonce)

    return ()
end

@external
func ac_withdraw{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    amount_or_token_id : felt,
    contract : felt,
    address : felt,
    nonce : felt):
    let (user) = get_caller_address()

    return _withdraw(user, amount_or_token_id, contract, address, nonce)
end

func _withdraw{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    amount_or_token_id : felt,
    contract : felt,
    address : felt,
    nonce : felt):
    alloc_locals

    check_on()
    assert_nn(amount_or_token_id)

    let (desc) = description.read(contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0

    let (org) = origin.read(amount_or_token_id, contract)
    if desc.kind == KIND_ERC20:
        let (bal) = balance.read(user=user, contract=contract)
        let new_balance = bal - amount_or_token_id
        assert_nn(new_balance)

        balance.write(user, contract, new_balance)
    else:
        let (usr) = owner.read(token_id=amount_or_token_id, contract=contract)
        assert usr = user

        owner.write(amount_or_token_id, contract, 0)
        origin.write(amount_or_token_id, contract, 0)
    end

    let (l1_caddr) = l1_contract_address.read()
    let (payload : felt*) = alloc()
    assert payload[0] = WITHDRAW
    assert payload[1] = address
    assert payload[2] = amount_or_token_id
    assert payload[3] = contract
    assert payload[4] = org
    assert payload[5] = nonce
    send_message_to_l1(
        to_address=l1_caddr,
        payload_size=6,
        payload=payload)

    return ()
end

@l1_handler
func deposit{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    from_address : felt,
    user : felt,
    amount_or_token_id : felt,
    contract : felt,
    nonce : felt):
    let (l1_caddr) = l1_contract_address.read()
    assert l1_caddr = from_address

    let (desc) = description.read(contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0

    if desc.kind == KIND_ERC20:
        let (bal) = balance.read(user=user, contract=contract)

        balance.write(user, contract, bal + amount_or_token_id)
    else:
        let (usr) = owner.read(token_id=amount_or_token_id, contract=contract)
        assert usr = 0

        owner.write(amount_or_token_id, contract, user)
    end

    return ()
end

@external
func transfer{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    from_ : felt,
    to_ : felt,
    amount_or_token_id : felt,
    contract : felt,
    nonce : felt):
    alloc_locals

    let inputs : felt* = alloc()
    inputs[0] = to_
    inputs[1] = amount_or_token_id
    inputs[2] = contract
    inputs[3] = nonce
    verify_inputs_by_signature(from_, 4, inputs)

    let ecdsa_ptr = ecdsa_ptr
    _transfer(from_, to_, amount_or_token_id, contract)

    return ()
end

@external
func ac_transfer{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    to_ : felt,
    amount_or_token_id : felt,
    contract : felt):
    let (caller) = get_caller_address()

    return _transfer(caller, to_, amount_or_token_id, contract)
end

func _transfer{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    from_ : felt,
    to_ : felt,
    amount_or_token_id : felt,
    contract : felt):
    check_on()
    assert_nn(amount_or_token_id)

    let (desc) = description.read(contract=contract)
    assert (desc.kind - KIND_ERC20) * (desc.kind - KIND_ERC721) = 0

    if desc.kind == KIND_ERC20:
        let (bal) = balance.read(user=from_, contract=contract)
        let new_balance = bal - amount_or_token_id
        assert_nn(new_balance)
        balance.write(from_, contract, new_balance)

        let (bal) = balance.read(user=to_, contract=contract)
        let new_balance = bal + amount_or_token_id
        assert_nn(new_balance)
        balance.write(to_, contract, new_balance)
    else:
        let (usr) = owner.read(token_id=amount_or_token_id, contract=contract)
        assert usr = from_

        owner.write(amount_or_token_id, contract, to_)
    end

    return ()
end

@external
func create_order{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    user : felt,
    bid : felt,
    base_contract : felt,
    base_token_id : felt,
    quote_contract : felt,
    quote_amount : felt):
    alloc_locals

    let inputs : felt* = alloc()
    inputs[0] = id
    inputs[1] = bid
    inputs[2] = base_contract
    inputs[3] = base_token_id
    inputs[4] = quote_contract
    inputs[5] = quote_amount
    verify_inputs_by_signature(user, 6, inputs)

    let ecdsa_ptr = ecdsa_ptr
    _create_order(id, user, bid, base_contract, base_token_id, quote_contract, quote_amount)

    return ()
end

@external
func ac_create_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    bid : felt,
    base_contract : felt,
    base_token_id : felt,
    quote_contract : felt,
    quote_amount : felt):
    let (caller) = get_caller_address()

    return _create_order(id, caller, bid, base_contract, base_token_id, quote_contract, quote_amount)
end

func _create_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    user : felt,
    bid : felt,
    base_contract : felt,
    base_token_id : felt,
    quote_contract : felt,
    quote_amount : felt):
    check_on()

    assert (bid - ASK) * (bid - BID) = 0
    assert_nn(quote_amount)

    let (ord) = order.read(id=id)
    assert ord.user = 0

    let (desc) = description.read(contract=base_contract)
    assert desc.kind = KIND_ERC721
    let (desc) = description.read(contract=quote_contract)
    assert desc.kind = KIND_ERC20
    if bid == ASK:
        let (usr) = owner.read(token_id=base_token_id, contract=base_contract)
        assert usr = user

        owner.write(base_token_id, base_contract, 0)
    else:
        let (bal) = balance.read(user=user, contract=quote_contract)
        let new_balance = bal - quote_amount
        assert_nn(new_balance)

        balance.write(user, quote_contract, new_balance)
    end

    order.write(id, LimitOrder(
        user=user,
        bid=bid,
        base_contract=base_contract,
        base_token_id=base_token_id,
        quote_contract=quote_contract,
        quote_amount=quote_amount,
        state=STATE_NEW))

    return ()
end

@external
func fulfill_order{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    user : felt,
    nonce : felt):
    alloc_locals

    let inputs : felt* = alloc()
    inputs[0] = id
    inputs[1] = nonce
    verify_inputs_by_signature(user, 2, inputs)

    let ecdsa_ptr = ecdsa_ptr
    _fulfill_order(id, user)

    return ()
end

@external
func ac_fulfill_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt):
    let (caller) = get_caller_address()

    return _fulfill_order(id, caller)
end

func _fulfill_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    user : felt):
    alloc_locals
    check_on()

    let (ord) = order.read(id)
    assert_not_zero(ord.user)
    assert ord.state = STATE_NEW

    if ord.bid == ASK:
        let (bal) = balance.read(user=user, contract=ord.quote_contract)
        let new_balance = bal - ord.quote_amount
        assert_nn(new_balance)
        balance.write(user, ord.quote_contract, new_balance)

        let (bal) = balance.read(user=ord.user, contract=ord.quote_contract)
        balance.write(ord.user, ord.quote_contract, bal + ord.quote_amount)

        let (usr) = owner.read(token_id=ord.base_token_id, contract=ord.base_contract)
        assert usr = 0
        owner.write(ord.base_token_id, ord.base_contract, user)
    else:
        let (usr) = owner.read(token_id=ord.base_token_id, contract=ord.base_contract)
        assert usr = user
        owner.write(ord.base_token_id, ord.base_contract, ord.user)

        let (bal) = balance.read(user=user, contract=ord.quote_contract)
        balance.write(user, ord.quote_contract, bal + ord.quote_amount)
    end

    order.write(id, LimitOrder(
        user=ord.user,
        bid=ord.bid,
        base_contract=ord.base_contract,
        base_token_id=ord.base_token_id,
        quote_contract=ord.quote_contract,
        quote_amount=ord.quote_amount,
        state=STATE_FULFILLED))

    return ()
end

@external
func cancel_order{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    nonce : felt):
    alloc_locals

    let (ord) = order.read(id)
    let inputs : felt* = alloc()
    inputs[0] = id
    inputs[1] = nonce
    verify_inputs_by_signature(ord.user, 2, inputs)

    let ecdsa_ptr = ecdsa_ptr
    _cancel_order(id, ord)

    return ()
end

@external
func ac_cancel_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt):
    let (caller) = get_caller_address()
    let (ord) = order.read(id)
    assert caller = ord.user

    return _cancel_order(id, ord)
end

func _cancel_order{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    id : felt,
    ord : LimitOrder):
    check_on()

    assert_not_zero(ord.user)
    assert ord.state = STATE_NEW

    if ord.bid == ASK:
        let (usr) = owner.read(token_id=ord.base_token_id, contract=ord.base_contract)
        assert usr = 0

        owner.write(ord.base_token_id, ord.base_contract, ord.user)
    else:
        let (bal) = balance.read(user=ord.user, contract=ord.quote_contract)
        let new_balance = bal + ord.quote_amount
        assert_nn(new_balance)

        balance.write(ord.user, ord.quote_contract, new_balance)
    end

    order.write(id, LimitOrder(
        user=ord.user,
        bid=ord.bid,
        base_contract=ord.base_contract,
        base_token_id=ord.base_token_id,
        quote_contract=ord.quote_contract,
        quote_amount=ord.quote_amount,
        state=STATE_CANCELLED))

    return ()
end

func check_on{
    syscall_ptr : felt*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}():
    let (paus) = pause.read()
    assert paus = 0

    return ()
end

func verify_inputs_by_signature{
    syscall_ptr : felt*,
    ecdsa_ptr : SignatureBuiltin*,
    pedersen_ptr : HashBuiltin*,
    range_check_ptr}(
    user : felt,
    n : felt,
    inputs : felt*):
    alloc_locals

    let (n_sig : felt, local sig : felt*) = get_tx_signature()
    assert n_sig = 2

    local syscall_ptr : felt* = syscall_ptr
    let (res) = hash_inputs(n, inputs)
    verify_ecdsa_signature(
        message=res,
        public_key=user,
        signature_r=sig[0],
        signature_s=sig[1])

    return ()
end

func hash_inputs{
    pedersen_ptr : HashBuiltin*}(
    n : felt, inputs : felt*) -> (
    result : felt):
    if n == 1:
        let (res) = hash2{hash_ptr=pedersen_ptr}(inputs[0], 0)

        return (result=res)
    end

    let (res) = hash_inputs(n - 1, inputs + 1)
    let (res) = hash2{hash_ptr=pedersen_ptr}(inputs[0], res)

    return (result=res)
end

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash_state import (
    hash_init, hash_update, hash_update_single, hash_finalize)
from starkware.cairo.common.math import assert_lt
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.starknet.common.syscalls import get_tx_signature
from admin import get_admin, change_admin
from facade import get_underpinning, underpin_with
from lib import authenticate
from ComposerInterface import ComposerInterface, Token, ARM_INPUT, ARM_OUTPUT

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt, admin : felt):
    underpin_with(underpinning)
    change_admin(admin)

    return ()
end

@external
func create_stereotype{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, admin : felt, user : felt):
    let (underpinning) = get_underpinning()
    ComposerInterface.create_stereotype(
        contract_address=underpinning, id=id, admin=admin, user=user)

    return ()
end

@external
func add_token{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        token_id : felt,
        contract : felt,
        io : felt,
        stereotype_id : felt,
        nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.admin, 5, &token_id)

    ComposerInterface.add_token(
        contract_address=underpinning,
        token_id=token_id,
        contract=contract,
        io=io,
        stereotype_id=stereotype_id)
    return ()
end

@external
func remove_token{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        token_id : felt, contract : felt, stereotype_id : felt, nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.admin, 4, &token_id)

    ComposerInterface.remove_token(
        contract_address=underpinning,
        token_id=token_id,
        contract=contract,
        stereotype_id=stereotype_id)
    return ()
end

@external
func activate_stereotype{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        id : felt, nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.admin, 2, &id)

    ComposerInterface.activate_stereotype(contract_address=underpinning, id=id)
    return ()
end

@external
func install_token{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        user : felt,
        token_id : felt,
        contract : felt,
        stereotype_id : felt,
        nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(user, 4, &token_id)

    ComposerInterface.install_token(
        contract_address=underpinning,
        user=user,
        token_id=token_id,
        contract=contract,
        stereotype_id=stereotype_id)
    return ()
end

@external
func uninstall_token{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        token_id : felt, contract : felt, stereotype_id : felt, nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.user, 4, &token_id)

    ComposerInterface.uninstall_token(
        contract_address=underpinning,
        token_id=token_id,
        contract=contract,
        stereotype_id=stereotype_id)
    return ()
end

@external
func execute_stereotype{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        id : felt, nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.user, 2, &id)

    ComposerInterface.execute_stereotype(contract_address=underpinning, id=id)
    return ()
end

@external
func launch_stereotype{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        id : felt,
        admin : felt,
        user : felt,
        inputs_len : felt, inputs : Token*,
        outputs_len : felt, outputs : Token*):
    alloc_locals

    assert_lt(0, inputs_len)
    assert_lt(0, outputs_len)
    let (sig_n : felt, sig : felt*) = get_tx_signature()
    assert sig_n = 2

    let hash_ptr = pedersen_ptr
    with hash_ptr:
        let (s) = hash_init()
        let (s) = hash_update_single(s, id)
        let (s) = hash_update_single(s, user)
        let (s) = hash_update(s, inputs, 2 * inputs_len)
        let (s) = hash_update(s, outputs, 2 * outputs_len)
        let (h) = hash_finalize(s)
        let pedersen_ptr = hash_ptr
    end
    verify_ecdsa_signature(
        message=h,
        public_key=admin,
        signature_r=sig[0],
        signature_s=sig[1])

    let (underpinning) = get_underpinning()
    ComposerInterface.create_stereotype(
        contract_address=underpinning, id=id, admin=admin, user=user)
    add_tokens(underpinning, id, ARM_INPUT, inputs_len, inputs)
    add_tokens(underpinning, id, ARM_OUTPUT, outputs_len, outputs)
    ComposerInterface.activate_stereotype(contract_address=underpinning, id=id)

    return ()
end

func add_tokens{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt,
        stereotype_id : felt,
        io : felt,
        tokens_len : felt,
        tokens : Token*):
    if tokens_len == 0:
        return ()
    end

    ComposerInterface.add_token(
        contract_address=underpinning,
        token_id=tokens[0].token_id,
        contract=tokens[0].contract,
        io=io,
        stereotype_id=stereotype_id)
    return add_tokens(underpinning, stereotype_id, io, tokens_len - 1, &tokens[1])
end

@external
func solve_stereotype{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        id : felt, nonce : felt):
    alloc_locals

    let (underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.user, 2, &id)

    install_tokens(underpinning, stereotype.user, id, 0, stereotype.inputs)
    ComposerInterface.execute_stereotype(contract_address=underpinning, id=id)

    return ()
end

func install_tokens{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        underpinning : felt, user : felt, stereotype_id : felt, i : felt, n : felt):
    if i == n:
        return ()
    end

    let (token) = ComposerInterface.get_token(
        contract_address=underpinning,
        stereotype_id=stereotype_id,
        arm=ARM_INPUT,
        i=i)
    let (install) = ComposerInterface.get_install(
        contract_address=underpinning,
        token_id=token.token_id,
        contract=token.contract)
    if install.stereotype_id == stereotype_id:
        return install_tokens(underpinning, user, stereotype_id, i + 1, n)
    end

    assert install.stereotype_id = 0
    ComposerInterface.install_token(
        contract_address=underpinning,
        user=user,
        token_id=token.token_id,
        contract=token.contract,
        stereotype_id=stereotype_id)

    return install_tokens(underpinning, user, stereotype_id, i + 1, n)
end

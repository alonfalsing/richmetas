%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from admin import get_admin, change_admin
from facade import get_underpinning, underpin_with
from lib import authenticate
from ComposerInterface import ComposerInterface

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
        io : felt,
        token_id : felt,
        contract : felt,
        stereotype_id : felt,
        nonce : felt):
    alloc_locals

    let (local underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.admin, 5, &io)

    ComposerInterface.add_token(
        contract_address=underpinning,
        io=io,
        token_id=token_id,
        contract=contract,
        stereotype_id=stereotype_id)
    return ()
end

@external
func remove_token{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        io : felt, i : felt, stereotype_id : felt, nonce : felt):
    alloc_locals

    let (local underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.admin, 4, &io)

    ComposerInterface.remove_token(
        contract_address=underpinning,
        io=io,
        i=i,
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

    let (local underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.admin, 2, &id)

    ComposerInterface.activate_stereotype(
        contract_address=underpinning, id=id)
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

    let (local underpinning) = get_underpinning()
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

    let (local underpinning) = get_underpinning()
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
func execute{
        syscall_ptr : felt*,
        ecdsa_ptr : SignatureBuiltin*,
        pedersen_ptr : HashBuiltin*,
        range_check_ptr}(
        stereotype_id : felt, nonce : felt):
    alloc_locals

    let (local underpinning) = get_underpinning()
    let (stereotype) = ComposerInterface.get_stereotype(
        contract_address=underpinning, id=stereotype_id)
    let (__fp__, _) = get_fp_and_pc()
    authenticate(stereotype.user, 2, &stereotype_id)

    ComposerInterface.execute(
        contract_address=underpinning, stereotype_id=stereotype_id)
    return ()
end

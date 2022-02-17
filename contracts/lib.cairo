%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.hash_state import hash_init, hash_update, hash_finalize
from starkware.cairo.common.signature import verify_ecdsa_signature
from starkware.starknet.common.syscalls import get_tx_signature

func authenticate{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, size : felt, data : felt*):
    alloc_locals

    let (sig_n : felt, local sig : felt*) = get_tx_signature()
    assert sig_n = 2

    let (h) = hash_message(size, data)
    verify_ecdsa_signature(
        message=h,
        public_key=user,
        signature_r=sig[0],
        signature_s=sig[1])

    return ()
end

func hash_message{
        pedersen_ptr : HashBuiltin*}(
        size : felt, data : felt*) -> (
        hash : felt):
    let (s) = hash_init()
    let (s) = hash_update{hash_ptr=pedersen_ptr}(s, data, size)
    let (h) = hash_finalize{hash_ptr=pedersen_ptr}(s)

    return (h)
end

func authenticate_r{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, size : felt, data : felt*):
    alloc_locals

    let (sig_n : felt, local sig : felt*) = get_tx_signature()
    assert sig_n = 2

    let (h) = hash_message_r(size, data)
    verify_ecdsa_signature(
        message=h,
        public_key=user,
        signature_r=sig[0],
        signature_s=sig[1])

    return ()
end

func hash_message_r{
        pedersen_ptr : HashBuiltin*}(
        size : felt, data : felt*) -> (
        hash : felt):
    if size == 1:
        let (h) = hash2{hash_ptr=pedersen_ptr}([data], 0)
    else:
        let (h) = hash_message_r(size - 1, data + 1)
        let (h) = hash2{hash_ptr=pedersen_ptr}([data], h)
    end

    return (h)
end

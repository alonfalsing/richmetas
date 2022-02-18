%lang starknet

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.starknet.common.syscalls import delegate_call, delegate_l1_handler, get_caller_address

@storage_var
func _Proxy_administrator() -> (address : felt):
end

@storage_var
func _Proxy_implementation() -> (address : felt):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        implementation : felt, administrator : felt):
    _Proxy_implementation.write(implementation)
    _Proxy_administrator.write(administrator)

    return ()
end

@view
func getAdmin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        administrator : felt):
    return _Proxy_administrator.read()
end

@external
func changeAdmin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        administrator : felt):
    onlyAdmin()
    _Proxy_administrator.write(administrator)

    return ()
end

@view
func getImplementation{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        implementation : felt):
    return _Proxy_implementation.read()
end

@external
func upgradeTo{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        implementation : felt):
    onlyAdmin()
    _Proxy_implementation.write(implementation)

    return ()
end

@external
@raw_input
@raw_output
func __default__{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        selector : felt, calldata_size : felt, calldata : felt*) -> (
        retdata_size : felt, retdata : felt*):
    let (address) = _Proxy_implementation.read()

    let (retdata_size, retdata : felt*) = delegate_call(
        contract_address=address, function_selector=selector, calldata_size=calldata_size, calldata=calldata)
    return (retdata_size=retdata_size, retdata=retdata)
end

@l1_handler
@raw_input
func __l1_default__{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        selector : felt, calldata_size : felt, calldata : felt*):
    let (address) = _Proxy_implementation.read()

    delegate_l1_handler(
        contract_address=address,
        function_selector=selector,
        calldata_size=calldata_size,
        calldata=calldata)
    return ()
end

func onlyAdmin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}():
    let (address) = get_caller_address()
    let (administrator) = _Proxy_administrator.read()

    assert address = administrator
    return ()
end

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin

@contract_interface
namespace UpgradeableProxy:
    func changeAdmin(administrator : felt):
    end

    func upgradeTo(implementation : felt):
    end
end

@storage_var
func _owner() -> (owner : felt):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        owner : felt):
    _owner.write(owner)

    return ()
end

@view
func owner{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        owner : felt):
    return _owner.read()
end

@external
func changeProxyAdmin{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        proxy : felt, administrator : felt):
    UpgradeableProxy.changeAdmin(contract_address=proxy, administrator=administrator)

    return ()
end

@external
func upgrade{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        proxy : felt, implementation : felt):
    UpgradeableProxy.upgradeTo(contract_address=proxy, implementation=implementation)

    return ()
end

%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from lib import authenticate

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
func getOwner{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        owner : felt):
    return _owner.read()
end

@external
func changeOwner{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, nonce : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 2, &user)
    _owner.write(user)

    return ()
end

@external
func changeProxyAdmin{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        proxy : felt, administrator : felt, nonce : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 3, &proxy)
    UpgradeableProxy.changeAdmin(contract_address=proxy, administrator=administrator)

    return ()
end

@external
func upgrade{
        syscall_ptr : felt*, ecdsa_ptr : SignatureBuiltin*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        proxy : felt, implementation : felt, nonce : felt):
    let (owner) = _owner.read()
    let (__fp__, _) = get_fp_and_pc()

    authenticate(owner, 3, &proxy)
    UpgradeableProxy.upgradeTo(contract_address=proxy, implementation=implementation)

    return ()
end

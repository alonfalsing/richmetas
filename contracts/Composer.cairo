%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_lt, assert_nn, assert_not_zero
from starkware.starknet.common.syscalls import get_contract_address
from acl import get_access, toggle_access, acl_secure
from admin import get_admin, change_admin
from LedgerInterface import LedgerInterface, KIND_ERC721
from ComposerInterface import Stereotype

const ARM_INPUT = 1
const ARM_OUTPUT = 2

const STATE_NEW = 0
const STATE_OPEN = 1
const STATE_READY = 2           # .inputs == .installed
const STATE_CLOSED = 4

struct Token:
    member token_id : felt
    member contract : felt
end

struct Install:
    member stereotype_id : felt
    member owner : felt
end

@storage_var
func _ledger() -> (address : felt):
end

@storage_var
func _stereotype(id : felt) -> (stereotype : Stereotype):
end

@storage_var
func _token(stereotype_id : felt, io : felt, i : felt) -> (token : Token):
end

# i/o arm
@storage_var
func _arm(
        token_id : felt, contract : felt, stereotype_id : felt) -> (
        arm : felt):
end

@storage_var
func _install(token_id : felt, contract : felt) -> (install : Install):
end

@constructor
func constructor{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ledger : felt, admin : felt):
    initialize(ledger)
    change_admin(admin)

    return ()
end

@external
func initialize{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ledger : felt):
    let (address) = _ledger.read()
    assert address = 0

    _ledger.write(ledger)
    return ()
end

@view
func get_ledger{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}() -> (
        address : felt):
    return _ledger.read()
end

@view
func get_stereotype{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt) -> (
        stereotype : Stereotype):
    return _stereotype.read(id)
end

@external
func create_stereotype{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt, admin : felt, user : felt):
    assert_not_zero(id)
    assert_not_zero(admin)
    assert_not_zero(user)
    let (stereotype) = _stereotype.read(id)
    assert stereotype.admin = 0

    _stereotype.write(id=id, value=Stereotype(
        inputs=0,
        outputs=0,
        installs=0,
        admin=admin,
        user=user,
        state=STATE_NEW))
    return ()
end

@external
func add_token{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        io : felt, token_id : felt, contract : felt, stereotype_id : felt):
    assert (io - ARM_INPUT) * (io - ARM_OUTPUT) = 0
    assert_nn(token_id)
    let (ledger) = _ledger.read()
    let (description) = LedgerInterface.describe(
        contract_address=ledger, contract=contract)
    assert description.kind = KIND_ERC721
    let (stereotype) = _stereotype.read(stereotype_id)
    assert stereotype.state = STATE_NEW
    assert (io - ARM_INPUT) * (description.mint - stereotype.admin) = 0
    let (arm) = _arm.read(
        token_id=token_id, contract=contract, stereotype_id=stereotype_id)
    assert arm = 0

    if io == ARM_INPUT:
        tempvar i = stereotype.inputs
        tempvar stereotype = Stereotype(
            inputs=stereotype.inputs + 1,
            outputs=stereotype.outputs,
            installs=0,
            admin=stereotype.admin,
            user=stereotype.user,
            state=STATE_NEW)
    else:
        # output
        tempvar i = stereotype.outputs
        tempvar stereotype = Stereotype(
            inputs=stereotype.inputs,
            outputs=stereotype.outputs + 1,
            installs=0,
            admin=stereotype.admin,
            user=stereotype.user,
            state=STATE_NEW)
    end
    let token = Token(token_id=token_id, contract=contract)
    _token.write(stereotype_id=stereotype_id, io=io, i=i, value=token)
    _arm.write(
        token_id=token_id,
        contract=contract,
        stereotype_id=stereotype_id,
        value=io)
    _stereotype.write(id=stereotype_id, value=stereotype)

    return ()
end

@external
func remove_token{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        io : felt, i : felt, stereotype_id : felt):
    assert (io - ARM_INPUT) * (io - ARM_OUTPUT) = 0
    assert_nn(i)
    let (stereotype) = _stereotype.read(stereotype_id)
    assert stereotype.state = STATE_NEW

    if io == ARM_INPUT:
        assert_lt(i, stereotype.inputs)
        let (tok) = _token.read(
            stereotype_id=stereotype_id, io=io, i=stereotype.inputs)
        tempvar token = tok
        tempvar stereotype = Stereotype(
            inputs=stereotype.inputs - 1,
            outputs=stereotype.outputs,
            installs=0,
            admin=stereotype.admin,
            user=stereotype.user,
            state=STATE_NEW)
    else:
        # output
        assert_lt(i, stereotype.outputs)
        let (tok) = _token.read(
            stereotype_id=stereotype_id, io=io, i=stereotype.outputs)
        tempvar token = tok
        tempvar stereotype = Stereotype(
            inputs=stereotype.inputs,
            outputs=stereotype.outputs - 1,
            installs=0,
            admin=stereotype.admin,
            user=stereotype.user,
            state=STATE_NEW)
    end
    let (old) = _token.read(stereotype_id=stereotype_id, io=io, i=i)
    _arm.write(
        token_id=old.token_id,
        contract=old.contract,
        stereotype_id=stereotype_id,
        value=0)
    _token.write(stereotype_id=stereotype_id, io=io, i=i, value=token)
    _stereotype.write(id=stereotype_id, value=stereotype)

    return ()
end

@external
func activate_stereotype{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        id : felt):
    let (stereotype) = _stereotype.read(id)
    assert stereotype.state = STATE_NEW
    assert_lt(0, stereotype.inputs)
    assert_lt(0, stereotype.outputs)

    _stereotype.write(id=id, value=Stereotype(
        inputs=stereotype.inputs,
        outputs=stereotype.outputs,
        installs=0,
        admin=stereotype.admin,
        user=stereotype.user,
        state=STATE_OPEN))
    return ()
end

@external
func install_token{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        user : felt, token_id : felt, contract : felt, stereotype_id : felt):
    let (ledger) = _ledger.read()
    let (owner) = LedgerInterface.get_owner(
        contract_address=ledger, token_id=token_id, contract=contract)
    assert user = owner
    let (stereotype) = _stereotype.read(stereotype_id)
    assert stereotype.state = STATE_OPEN
    let (install) = _install.read(token_id, contract)
    assert install.stereotype_id = 0
    let (arm) = _arm.read(
        token_id=token_id, contract=contract, stereotype_id=stereotype_id)
    assert arm = ARM_INPUT

    let (address) = get_contract_address()
    LedgerInterface.transfer(
        contract_address=ledger,
        from_=user,
        to_=address,
        amount_or_token_id=token_id,
        contract=contract)
    _install.write(token_id=token_id, contract=contract, value=Install(
        stereotype_id=stereotype_id,
        owner=user))
    _stereotype.write(id=stereotype_id, value=Stereotype(
        inputs=stereotype.inputs,
        outputs=stereotype.outputs,
        installs=stereotype.installs + 1,
        admin=stereotype.admin,
        user=stereotype.user,
        state=STATE_OPEN))

    return ()
end

@external
func uninstall_token{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        token_id : felt, contract : felt, stereotype_id : felt):
    let (stereotype) = _stereotype.read(stereotype_id)
    assert stereotype.state = STATE_OPEN
    let (install) = _install.read(token_id, contract)
    assert install.stereotype_id = stereotype_id

    let (ledger) = _ledger.read()
    let (address) = get_contract_address()
    LedgerInterface.transfer(
        contract_address=ledger,
        from_=address,
        to_=install.owner,
        amount_or_token_id=token_id,
        contract=contract)
    _install.write(token_id=token_id, contract=contract, value=Install(
        stereotype_id=0, owner=0))
    _stereotype.write(id=stereotype_id, value=Stereotype(
        inputs=stereotype.inputs,
        outputs=stereotype.outputs,
        installs=stereotype.installs - 1,
        admin=stereotype.admin,
        user=stereotype.user,
        state=STATE_OPEN))

    return ()
end

@external
func execute{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        stereotype_id : felt):
    alloc_locals

    let (local stereotype) = _stereotype.read(stereotype_id)
    assert stereotype.state = STATE_OPEN
    assert stereotype.inputs = stereotype.installs

    let (ledger) = _ledger.read()
    mint(stereotype, stereotype_id, 0, ledger)
    _stereotype.write(id=stereotype_id, value=Stereotype(
        inputs=stereotype.inputs,
        outputs=stereotype.outputs,
        installs=stereotype.installs,
        admin=stereotype.admin,
        user=stereotype.user,
        state=STATE_CLOSED))

    return ()
end

func mint{
        syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        stereotype : Stereotype, stereotype_id : felt, i : felt, ledger : felt):
    if i == stereotype.outputs:
        return ()
    end

    let (token) = _token.read(stereotype_id=stereotype_id, io=ARM_OUTPUT, i=i)
    LedgerInterface.mint(
        contract_address=ledger,
        user=stereotype.user,
        token_id=token.token_id,
        contract=token.contract)

    return mint(stereotype, stereotype_id, i + 1, ledger)
end

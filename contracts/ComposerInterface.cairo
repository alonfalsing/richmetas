%lang starknet

struct Stereotype:
    member inputs : felt
    member outputs : felt
    member installs : felt
    member admin : felt         # add / remove / activate
    member user : felt          # install / uninstall / execute
    member state : felt
end

@contract_interface
namespace ComposerInterface:
    func get_stereotype(id : felt) -> (stereotype : Stereotype):
    end

    func create_stereotype(id : felt, admin : felt, user : felt):
    end

    func add_token(token_id : felt, contract : felt, io : felt, stereotype_id : felt):
    end

    func remove_token(token_id : felt, contract : felt, stereotype_id : felt):
    end

    func activate_stereotype(id : felt):
    end

    func install_token(user : felt, token_id : felt, contract : felt, stereotype_id : felt):
    end

    func uninstall_token(token_id : felt, contract : felt, stereotype_id : felt):
    end

    func execute_stereotype(id : felt):
    end
end

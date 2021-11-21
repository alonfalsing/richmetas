// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import "./IMintable.sol";
import "./IStarknetCore.sol";

contract Fluence is IERC721Receiver {
    enum TokenType { Z, ERC20, ERC721 }

    uint256 constant WITHDRAW = 0;
    uint256 constant DEPOSIT = 0xc73f681176fc7b3f9693986fd7b14581e8d540519e27400e88b8713932be01;

    IStarknetCore starknetCore;
    mapping(address => TokenType) public contracts;

    constructor(IStarknetCore starknetCore_, IERC20 erc20_, IERC721 erc721_) {
        starknetCore = starknetCore_;

        contracts[address(erc20_)] = TokenType.ERC20;
        contracts[address(erc721_)] = TokenType.ERC721;
    }

    function deposit(uint256 toContract, uint256 user) external payable {
        uint256[] memory payload = new uint256[](3);
        payload[0] = user;
        payload[1] = msg.value;
        payload[2] = 0;
        starknetCore.sendMessageToL2(toContract, DEPOSIT, payload);
    }

    function deposit(uint256 toContract, uint256 user, uint256 amountOrId, address fromContract) external {
        TokenType typ_ = contracts[fromContract];
        require(typ_ != TokenType.Z, "Unregistered contract.");

        if (typ_ == TokenType.ERC20) {
            IERC20 erc20 = IERC20(fromContract);
            erc20.transferFrom(msg.sender, address(this), amountOrId);
        } else {
            IERC721 erc721 = IERC721(fromContract);
            erc721.safeTransferFrom(msg.sender, address(this), amountOrId);
        }

        uint256[] memory payload = new uint256[](3);
        payload[0] = user;
        payload[1] = amountOrId;
        payload[2] = uint160(fromContract);
        starknetCore.sendMessageToL2(toContract, DEPOSIT, payload);
    }

    function withdraw(uint256 fromContract, address payable user, uint256 amountOrId, address toContract, bool mint) external {
        TokenType typ_ = contracts[toContract];
        require(toContract == address(0) || typ_ != TokenType.Z, "Unregistered contract.");

        uint256[] memory payload = new uint256[](5);
        payload[0] = WITHDRAW;
        payload[1] = uint160(msg.sender);
        payload[2] = amountOrId;
        payload[3] = uint160(toContract);
	payload[4] = mint ? 1 : 0;
        starknetCore.consumeMessageFromL2(fromContract, payload);

        if (toContract == address(0)) {
            user.transfer(amountOrId);
        } else if (typ_ == TokenType.ERC20) {
            IERC20(toContract).transfer(user, amountOrId);
        } else if (mint) {
	    IMintable(toContract).mintFor(user, amountOrId);
	} else {
            IERC721(toContract).safeTransferFrom(address(this), user, amountOrId);
        }
    }

    function onERC721Received(
        address /* operator */,
        address /* from */,
        uint256 /* tokenId */,
        bytes calldata /* data */
    ) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }
}
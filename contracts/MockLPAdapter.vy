# @version 0.3.7

from vyper.interfaces import ERC20
import LPAdapter as LPAdapter

interface mintableERC20:
    def mint(_receiver: address, _amount: uint256) -> uint256: nonpayable
    def burn(_value: uint256): nonpayable
    

implements: LPAdapter

aoriginalAsset: immutable(address)
awrappedAsset: immutable(address)
adapterLPAddr: immutable(address)

@external
def __init__(_originalAsset: address, _wrappedAsset: address):
    aoriginalAsset = _originalAsset
    awrappedAsset = _wrappedAsset
    adapterLPAddr = self


@external
@pure
def originalAsset() -> address: return aoriginalAsset


@external
@pure
def wrappedAsset() -> address: return awrappedAsset


@internal
@view
def _convertToShares(_asset_amount: uint256) -> uint256:
    # return _asset_amount

    shareQty : uint256 = ERC20(awrappedAsset).totalSupply()
    assetQty : uint256 = ERC20(aoriginalAsset).balanceOf(self)

    # If there aren't any shares yet it's going to be 1:1.
    if shareQty == 0 : return _asset_amount
    
    sharesPerAsset : uint256 = assetQty / shareQty
    return _asset_amount * sharesPerAsset 


@external
@view
def convertToShares(_asset_amount: uint256) -> uint256: return self._convertToShares(_asset_amount)


@internal
@view
def _convertToAssets(_share_amount: uint256) -> uint256:
    # return _share_amount

    shareQty : uint256 = ERC20(awrappedAsset).totalSupply()
    assetQty : uint256 = ERC20(aoriginalAsset).balanceOf(self)

    # If there aren't any shares yet it's going to be 1:1.
    if shareQty == 0: return _share_amount
    
    assetsPerShare : uint256 = shareQty / assetQty
    return _share_amount * assetsPerShare


@external
@view
def convertToAssets(_share_amount: uint256) -> uint256: return self._convertToAssets(_share_amount)


#How much asset can be withdrawn in a single call
@external
@view
def maxWithdraw() -> uint256: 
    return self._convertToAssets(ERC20(awrappedAsset).balanceOf(msg.sender))


#How much asset can be deposited in a single call
@external
@view
def maxDeposit() -> uint256: 
    return max_value(uint256)


@external
@view
def totalAssets() -> uint256:
    return ERC20(aoriginalAsset).balanceOf(adapterLPAddr)


# Deposit the asset into underlying LP. The tokens must be present inside the 4626 vault.
@external
@nonpayable
def deposit(asset_amount: uint256):
    # Move funds into the LP.
    ERC20(aoriginalAsset).transfer(adapterLPAddr, asset_amount)

    # Return LP wrapped assets to 4626 vault.
    mintableERC20(awrappedAsset).mint(self, asset_amount) 


# Withdraw the asset from the LP to an arbitary address. 
@external
@nonpayable
def withdraw(asset_amount: uint256 , withdraw_to: address):
    # Destroy the wrapped assets
    mintableERC20(awrappedAsset).burn(asset_amount)

    assert ERC20(aoriginalAsset).balanceOf(adapterLPAddr) >= asset_amount, "INSUFFICIENT FUNDS!"
    assert ERC20(aoriginalAsset).allowance(adapterLPAddr, self) >= asset_amount, "NO APPROVAL!"

    # Move funds into the destination accout.
    ERC20(aoriginalAsset).transferFrom(adapterLPAddr, withdraw_to, asset_amount)


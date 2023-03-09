# @version 0.3.7
from vyper.interfaces import ERC20
import LPAdapter as LPAdapter
#This contract would only be called using delegate call, so we do
# not use this contract's storage. Only immutable or constant.
#If there is a strong reason for having storage, then the storage slots
# need to be carefully co-ordinated with the upstream 4626


#Looks like the following line does not enforce compatibility
implements: LPAdapter

#Address of underlying asset we are investing
originalAsset: immutable(address)
#Address of Compound v2 Token. we withdraw and deposit against this
wrappedAsset: immutable(address)
#Address of euler protocal vault (needed as allowance target)
euler: immutable(address)
adapterAddr: immutable(address)

interface EulerToken:
    #Transfer underlying tokens from sender to the Euler pool, and increase account's eTokens
    #It appears subAccountId would always be 0
    #The amount is denominated in underlying tokens
    def deposit(subAccountId: uint256, amount: uint256): nonpayable
    #Transfer underlying tokens from Euler pool to sender, and decrease account's eTokens
    #It appears subAccountId would always be 0
    #amount In underlying units
    def withdraw(subAccountId: uint256, amount: uint256): nonpayable
    #Balance of a particular account, in underlying units (increases as interest is earned)
    def balanceOfUnderlying(account: address) -> uint256: view
    #Convert an eToken balance to an underlying amount, taking into account current exchange rate
    def convertBalanceToUnderlying(balance: uint256) -> uint256: view
    #Convert an underlying amount to an eToken balance, taking into account current exchange rate
    def convertUnderlyingToBalance(underlyingAmount: uint256) -> uint256: view
    #Balance of the reserves, in underlying units (increases as interest is earned)
    def reserveBalanceUnderlying() -> uint256: view
    def touch(): nonpayable
    def underlyingAsset() -> address: view
    

@external
def __init__(_originalAsset: address, _wrappedAsset: address, _euler: address):
    originalAsset = _originalAsset
    wrappedAsset = _wrappedAsset
    euler = _euler
    adapterAddr = self
    assert EulerToken(_wrappedAsset).underlyingAsset() == _originalAsset, "eToken <--> asset mismatch"


#Workaround because vyper does not allow doing delegatecall from inside view.
#we do a static call instead, but need to fix the correct vault location for queries.
@internal
@view
def vault_location() -> address:
    if self == adapterAddr:
        #if "self" is adapter, meaning this is not delegate call and we treat msg.sender as the vault
        return msg.sender
    #Otherwise we are inside DELEGATECALL, therefore self would be the 4626
    return self

@internal
@view
def assettoetoken(asset: uint256) -> uint256:
    return EulerToken(wrappedAsset).convertUnderlyingToBalance(asset)

@internal
@view
def etokentoasset(wrapped: uint256) -> uint256:
    return EulerToken(wrappedAsset).convertBalanceToUnderlying(wrapped)


#How much asset can be withdrawn in a single transaction
@external
@view
def maxWithdraw() -> uint256:
    #How much original asset is currently available in the e-token contract
    cash: uint256 = EulerToken(wrappedAsset).reserveBalanceUnderlying() #asset
    return min(cash, self._assetBalance())

#How much asset can be deposited in a single transaction
@external
@view
def maxDeposit() -> uint256:
    return max_value(uint256)


#How much asset this LP is responsible for.
@external
@view
def totalAssets() -> uint256:
    return self._assetBalance()

@internal
@view
def _assetBalance() -> uint256:
    return EulerToken(wrappedAsset).balanceOfUnderlying(self.vault_location())

#Deposit the asset into underlying LP
@external
@nonpayable
def deposit(asset_amount: uint256):
    #TODO: NEED SAFE ERC20
    #Approve lending pool
    ERC20(originalAsset).approve(euler, asset_amount)
    #Call deposit function
    EulerToken(wrappedAsset).deposit(0, asset_amount)
    # EulerToken(wrappedAsset).touch()

#Withdraw the asset from the LP
@external
@nonpayable
def withdraw(asset_amount: uint256 , withdraw_to: address):
    #Could not find withdrawTo in Euler's eToken
    EulerToken(wrappedAsset).withdraw(0, asset_amount)
    if withdraw_to != self:
        ERC20(originalAsset).transfer(withdraw_to, asset_amount)

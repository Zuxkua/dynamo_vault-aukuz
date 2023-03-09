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
adapterAddr: immutable(address)

DIVISOR: constant(uint256) = 10**18

interface CompoundToken:
    #Sender supplies assets into the market and receives cTokens in exchange
    #Accrues interest whether or not the operation succeeds, unless reverted
    def mint(mintAmount: uint256) -> uint256: nonpayable
    #Sender redeems cTokens in exchange for a specified amount of underlying asset
    #Accrues interest whether or not the operation succeeds, unless reverted
    def redeemUnderlying(redeemTokens: uint256) -> uint256: nonpayable
    #Calculates the exchange rate from the underlying to the CToken
    #This function does not accrue interest before calculating the exchange rate
    #Calculated exchange rate scaled by 1e18
    def exchangeRateStored()  -> uint256: view
    #Get the underlying balance of the `owner`
    #This also accrues interest in a transaction
    #This is not a view and changes storage, so maybe we only rely on exchangeRateStored
    def balanceOfUnderlying(owner: address) -> uint256: nonpayable
    

@external
def __init__(_originalAsset: address, _wrappedAsset: address):
    originalAsset = _originalAsset
    wrappedAsset = _wrappedAsset
    adapterAddr = self

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
def asettoctoken(asset: uint256) -> uint256:
    #we use stored exchange rate, worst case our view functions might be very slightly off
    exchange_rate: uint256 = CompoundToken(wrappedAsset).exchangeRateStored()
    return (asset * DIVISOR) / exchange_rate

@internal
@view
def ctokentoaset(wrapped: uint256) -> uint256:
    #we use stored exchange rate, worst case our view functions might be very slightly off
    exchange_rate: uint256 = CompoundToken(wrappedAsset).exchangeRateStored()
    return (wrapped * exchange_rate) / DIVISOR


#How much asset can be withdrawn in a single transaction
@external
@view
def maxWithdraw() -> uint256:
    #TODO: There are additional checks unaccounted here
    #How much original asset is currently available in the c-token contract
    cash: uint256 = ERC20(originalAsset).balanceOf(wrappedAsset) #asset
    return min(cash, self._assetBalance())

#How much asset can be deposited in a single transaction
@external
@view
def maxDeposit() -> uint256:
    #TODO: There are additional checks unaccounted here
    return max_value(uint256)


#How much asset this LP is responsible for.
@external
@view
def totalAssets() -> uint256:
    return self._assetBalance()

@internal
@view
def _assetBalance() -> uint256:
    wrappedBalance: uint256 = ERC20(wrappedAsset).balanceOf(self.vault_location()) #aToken
    unWrappedBalance: uint256 = self.ctokentoaset(wrappedBalance) #asset
    return unWrappedBalance


#Need to make this proxy method because vyper needs type defined before initiating uint2str
@internal
@pure
def stringify(b: uint256) -> String[78]:
    return uint2str(b)


#Deposit the asset into underlying LP
@external
@nonpayable
def deposit(asset_amount: uint256):
    #TODO: NEED SAFE ERC20
    #Approve lending pool
    ERC20(originalAsset).approve(wrappedAsset, asset_amount)
    #Call deposit function
    #"deposit_from" does not make sense. this is the beneficiary of a-tokens which must always be our vault.
    #check for returned error code!!!
    err: uint256 = CompoundToken(wrappedAsset).mint(asset_amount)
    #uint 0=success, otherwise a failure (see ErrorReporter.sol for details)
    assert err == 0, concat( "Compound mint: ", self.stringify(err))

#Withdraw the asset from the LP
@external
@nonpayable
def withdraw(asset_amount: uint256 , withdraw_to: address):
    #Could not find redeemTo in compound v2
    err: uint256 = CompoundToken(wrappedAsset).redeemUnderlying(asset_amount)
    #uint 0=success, otherwise a failure (see ErrorReporter.sol for details)
    assert err == 0, concat( "Compound redeem: ", self.stringify(err))
    if withdraw_to != self:
        ERC20(originalAsset).transfer(withdraw_to, asset_amount)

# @version 0.3.7


#Declaring interface in this format allows it to be "compiled", so we can use its ABI from python side
#One happy side-effect is now "implements" bit is enforced in other contracts.

# How much asset can be withdrawn in a single call
@external
@view
def maxWithdraw() -> uint256:
    return 0

# How much asset can be deposited in a single call
@external
@view
def maxDeposit() -> uint256:
    return 0

# How much asset this LP is responsible for.
@external
@view
def totalAssets() -> uint256:
    return 0


# Deposit the asset into underlying LP. The tokens must be present inside the 4626 vault.
@external
def deposit(asset_amount: uint256):
    pass


# Withdraw the asset from the LP to an arbitary address. 
@external
def withdraw(asset_amount: uint256 , withdraw_to: address):
    pass

# @version 0.3.7

interface LPAdapter:
    # How much asset can be withdrawn in a single call
    def maxWithdraw() -> uint256: view
    # How much asset can be deposited in a single call
    def maxDeposit() -> uint256: view
    # How much asset this LP is responsible for.
    def totalAssets() -> uint256: view
    # Deposit the asset into underlying LP. The tokens must be present inside the 4626 vault.
    def deposit(asset_amount: uint256): nonpayable
    # Withdraw the asset from the LP to an arbitary address. 
    def withdraw(asset_amount: uint256 , withdraw_to: address): nonpayable

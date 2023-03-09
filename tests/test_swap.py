import pytest

import ape
from tests.conftest import ensure_hardhat
from web3 import Web3

#ETH Mainnet addrs
WETH  = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
BAL   = "0xba100000625a3754423978a60c9317c58a424e3D"
POOL_BAL_WETH = "0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56"
pool_BAL_WETH = "0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014"
VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"

@pytest.fixture
def weth(project):
    return project.IERC20.at(WETH)

@pytest.fixture
def bal(project):
    return project.IERC20.at(BAL)

@pytest.fixture
def vault(project):
    return project.Vault.at(VAULT)

#@pytest.mark.skipif(is_not_hard_hat(), reason="Only run when connected to hard hat.")
def test_fork(vault, ensure_hardhat):
    #Evidence of connecting to the real balancer vault contract on mainnet fork
    assert vault.WETH() == WETH

def test_always_good():
    assert True

def test_swap(vault, accounts, weth, bal, ensure_hardhat):
    trader = accounts[0]
    print(trader)
    #let trader wrap 100 ETH
    trader.transfer(WETH, "100 Ether")
    print("WETH", weth.balanceOf(trader))
    print("BAL", bal.balanceOf(trader))
    # Approve the Vault spend trader's WETH
    weth.approve(VAULT, "100000 Ether", sender=trader)

    struct_single_swap = (
        pool_BAL_WETH, #bytes32 poolId
        0, #SwapKind kind
        WETH, #IAsset assetIn
        BAL, #IAsset assetOut
        "1 Ether", #uint256 amount
        b"" #bytes userData
    )

    struct_fund_management = (
        trader, #address sender
        False, #bool fromInternalBalance
        trader, #address payable recipient
        False #bool toInternalBalance
    )

    vault.swap(
        struct_single_swap, #SingleSwap singleSwap
        struct_fund_management, #FundManagement funds
        "1 Ether", #uint256 limit
        999999999999999999, #uint256 deadline
        sender=trader
    )

    print("WETH", weth.balanceOf(trader))
    print("BAL", bal.balanceOf(trader))
    assert weth.balanceOf(trader) == Web3.to_wei(99, 'ether')
    #copied this from output of prior run.
    #should be consistent as we fork off a specific block each time
    assert bal.balanceOf(trader) == 232212803034529744021

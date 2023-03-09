import pytest

import ape
from tests.conftest import ensure_hardhat
from web3 import Web3
from eth_abi import encode

#ETH Mainnet addrs
VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"

@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def trader(accounts):
    return accounts[1]

@pytest.fixture
def vault(project):
    return project.Vault.at(VAULT)

@pytest.fixture
def dai(project, deployer, trader, ensure_hardhat):
    ua = deployer.deploy(project.ERC20, "DAI", "DAI", 18, 0, deployer)
    ua.mint(trader, '5000000000 Ether', sender=deployer)
    ua.approve(VAULT, '5000000000 Ether', sender=trader)
    return ua

@pytest.fixture
def frax(project, deployer, trader, ensure_hardhat):
    ua = deployer.deploy(project.ERC20, "FRAX", "FRAX", 18, 0, deployer)
    ua.mint(trader, '5000000000 Ether', sender=deployer)
    ua.approve(VAULT, '5000000000 Ether', sender=trader)
    return ua

@pytest.fixture
def gho(project, deployer, trader, ensure_hardhat):
    ua = deployer.deploy(project.ERC20, "GHO", "GHO", 18, 0, deployer)
    ua.mint(trader, '5000000000 Ether', sender=deployer)
    ua.approve(VAULT, '5000000000 Ether', sender=trader)
    return ua

@pytest.fixture
def ddai4626(project, deployer, trader, dai, ensure_hardhat):
    ua = deployer.deploy(project.Fake4626, "Wrapped DAI", "dDAI4626", 18, dai)
    dai.approve(ua, '2000000000 Ether', sender=trader)
    ua.deposit('1000 Ether', trader, sender=trader)
    ua.approve(VAULT, '1000000000 Ether', sender=trader)
    return ua

@pytest.fixture
def dfrax4626(project, deployer, trader, frax, ensure_hardhat):
    ua = deployer.deploy(project.Fake4626, "Wrapped FRAX", "dFRAX4626", 18, frax)
    frax.approve(ua, '2000000000 Ether', sender=trader)
    ua.deposit('1000 Ether', trader, sender=trader)
    ua.approve(VAULT, '1000000000 Ether', sender=trader)
    return ua

@pytest.fixture
def dgho4626(project, deployer, trader, gho, ensure_hardhat):
    ua = deployer.deploy(project.Fake4626, "Wrapped GHO", "dGHO4626", 18, gho)
    gho.approve(ua, '2000000000 Ether', sender=trader)
    ua.deposit('1000 Ether', trader, sender=trader)
    ua.approve(VAULT, '1000000000 Ether', sender=trader)
    return ua

def swap(pool_id, vault, intoken, outtoken, amount, trader):
    struct_single_swap = (
        pool_id, #bytes32 poolId
        1, #SwapKind kind
        intoken, #IAsset assetIn
        outtoken, #IAsset assetOut
        amount, #uint256 amount
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
        "20000000000 Ether", #uint256 limit
        999999999999999999, #uint256 deadline
        sender=trader
    )

@pytest.fixture
def dDAI(project, deployer, dai, ddai4626, vault, trader, ensure_hardhat):
    lp = deployer.deploy(
        #We are using mock here which hardcodes exchange rate of 1:1
        #TODO: once we have a somewhat working 4626, we should probably use ERC4626LinearPool
        project.ERC4626LinearPool,
        vault,
        "DAI 4626 linear pool",
        "dDAI",
        dai, #mainToken
        ddai4626, #wrappedToken
        2100000000000000000000000, #upperTarget = 2100000.0 DAI (by default lower target is 0, can be raised after enough liquidity is present)
        10000000000000, #swapFeePercentage = 0.001% (10000000000000 = 10^13 ; 10^18/10^13 = 100000; 100 / 100000 = 0.001%)
        7332168, #pauseWindowDuration
        2592000, #bufferPeriodDuration
        deployer
    )
    #Copied some constructor args from https://etherscan.io/token/0x804cdb9116a10bb78768d3252355a1b18067bf8f#code
    lp.initialize(sender=deployer)
    #Create some liquidity to avoid BAL#004 (ZERO_DIVISION)
    pool_id = lp.getPoolId()
    swap(pool_id, vault, dai, lp, "1000 Ether", trader)
    swap(pool_id, vault, ddai4626, lp, "1000 Ether", trader)
    return lp

@pytest.fixture
def dFRAX(project, deployer, frax, dfrax4626, vault, trader, ensure_hardhat):
    lp = deployer.deploy(
        #We are using mock here which hardcodes exchange rate of 1:1
        #TODO: once we have a somewhat working 4626, we should probably use ERC4626LinearPool
        project.ERC4626LinearPool,
        vault,
        "FRAX 4626 linear pool",
        "dFRAX",
        frax, #mainToken
        dfrax4626, #wrappedToken
        2100000000000000000000000, #upperTarget = 2100000.0 DAI (by default lower target is 0, can be raised after enough liquidity is present)
        10000000000000, #swapFeePercentage = 0.001% (10000000000000 = 10^13 ; 10^18/10^13 = 100000; 100 / 100000 = 0.001%)
        7332168, #pauseWindowDuration
        2592000, #bufferPeriodDuration
        deployer
    )
    #Copied some constructor args from https://etherscan.io/token/0x804cdb9116a10bb78768d3252355a1b18067bf8f#code
    lp.initialize(sender=deployer)
    #Create some liquidity to avoid BAL#004 (ZERO_DIVISION)
    pool_id = lp.getPoolId()
    swap(pool_id, vault, frax, lp, "1000 Ether", trader)
    swap(pool_id, vault, dfrax4626, lp, "1000 Ether", trader)
    return lp

@pytest.fixture
def dGHO(project, deployer, gho, dgho4626, vault, trader, ensure_hardhat):
    lp = deployer.deploy(
        #We are using mock here which hardcodes exchange rate of 1:1
        #TODO: once we have a somewhat working 4626, we should probably use ERC4626LinearPool
        project.ERC4626LinearPool,
        VAULT,
        "GHO 4626 linear pool",
        "dGHO",
        gho, #mainToken
        dgho4626, #wrappedToken
        2100000000000000000000000, #upperTarget = 2100000.0 DAI (by default lower target is 0, can be raised after enough liquidity is present)
        10000000000000, #swapFeePercentage = 0.001% (10000000000000 = 10^13 ; 10^18/10^13 = 100000; 100 / 100000 = 0.001%)
        7332168, #pauseWindowDuration
        2592000, #bufferPeriodDuration
        deployer
    )
    #Copied some constructor args from https://etherscan.io/token/0x804cdb9116a10bb78768d3252355a1b18067bf8f#code
    lp.initialize(sender=deployer)
    #Create some liquidity to avoid BAL#004 (ZERO_DIVISION)
    pool_id = lp.getPoolId()
    swap(pool_id, vault, gho, lp, "1000 Ether", trader)
    swap(pool_id, vault, dgho4626, lp, "1000 Ether", trader)
    return lp

@pytest.fixture
def dUSD(project, deployer, vault, dai, frax, gho, dDAI, dFRAX, dGHO, ensure_hardhat):
    #Example pool: https://etherscan.io/address/0xa13a9247ea42d743238089903570127dda72fe44
    sp = deployer.deploy(
        project.ComposableStablePool,
        (
            vault, #vault
            "0x97207B095e4D5C9a6e4cfbfcd2C3358E03B90c4A", #protocolFeeProvider: dunno copied from existing pool
            "dUSD", #name
            "dUSD", #symbol
            [dDAI, dFRAX, dGHO], #tokens
            [dDAI, dFRAX, dGHO], #rateProviders: Linearpool themselves are oracles
            #Do we need some other price oracle too to account for potential difference in price between stablecoins?
            [0, 0, 0], #tokenRateCacheDurations: Does 0 disable caching?
            [False,False,False], #exemptFromYieldProtocolFeeFlags: ???
            1472, #amplificationParameter: ??
            100000000000000, #swapFeePercentage: ??
            0, #pauseWindowDuration
            0, #bufferPeriodDuration
            deployer, #owner
            "no idea" #version
        )
    )
    # sp.initialize(sender=deployer)
    return sp

def tokendiff(user, tokens, prev={}):
    for token in tokens.keys():
        bal = tokens[token].balanceOf(user) / 10**18
        prev_bal = prev.get(token, 0)
        print("{token}\t: {bal:.4f} ({delta:+.4f})".format(token=token, bal=bal, delta=bal - prev_bal))
        prev[token] = bal
    return prev

def test_composable(trader, vault, dai, frax, gho, dDAI, dFRAX, dGHO, dUSD, ddai4626, dfrax4626, dgho4626, ensure_hardhat):
    #ensure oracle of each d-token returns 1 (since no yield yet)
    assert dDAI.getRate() == 10**18, "rate is not 1"
    assert dFRAX.getRate() == 10**18, "rate is not 1"
    assert dGHO.getRate() == 10**18, "rate is not 1"
    dUSD_pool_id = dUSD.getPoolId()
    # assert dUSD.getRate() == 10**18, "rate is not 1"
    tokens = {
        "DAI": dai,
        "dDAI": dDAI,
        "dFRAX": dFRAX,
        "dGHO": dGHO,
        "dUSD": dUSD
    }
    bal = tokendiff(trader, tokens)
    #Invest some LP tokens into the stable pool 
    #No idea where 5192296858534827628530496329000000 figure came from
    #Copied init args from https://etherscan.io/tx/0x9a23e5a994b1b8bab3b9fa28a7595ef64aa0d4dd115ae5c41e802f0d84aa4a71
    #Add $1 of each stable coin.
    vault.joinPool(
        dUSD_pool_id,
        trader, #sender
        trader, #recipient
        (
            [dDAI, dFRAX, dGHO, dUSD], #assets
            ["1 Ether", "1 Ether", "1 Ether", 5192296858534827628530496329000000], #maxAmountsIn
            encode(['uint256', 'uint256[]'], [
                0, #JoinKind.INIT
                (
                    1000000000000000000,
                    1000000000000000000,
                    1000000000000000000,
                    5192296858534827628530496329000000
                )
            ]  ), #bytes userData
            False #fromInternalBalance
        ),
        sender=trader
    )
    bal = tokendiff(trader, tokens, bal)
    #Lets add some more... 200 dDAI, 150 dFRAX and 100 dGHO for < 450 dUSD (because of fees)
    vault.joinPool(
        dUSD_pool_id,
        trader, #sender
        trader, #recipient
        (
            [dDAI, dFRAX, dGHO, dUSD], #assets
            ["200 Ether", "150 Ether", "100 Ether", '449 Ether'], #maxAmountsIn
            encode(['uint256', 'uint256[]', 'uint256'], [
                1, #JoinKind.EXACT_TOKENS_IN_FOR_BPT_OUT
                (
                    200*10**18, #dDAI
                    150*10**18, #dFRAX
                    100*10**18 #dGHO
                ), #amountsIn
                449*10**18 #minimumBPT
            ]  ), #bytes userData
            False #fromInternalBalance
        ),
        sender=trader
    )
    bal = tokendiff(trader, tokens, bal)
    #Inflate dDAI4526 value by 2x to probe yield things
    #At the moment dDAI is backed by $1000 in DAI and $1000 in ddai4626
    #If value of ddai4626 becomes 2x then value of dDAI is now $3000, 
    #i.e. 1 dDAI = 1.5 DAI
    dai.transfer(ddai4626, '1000 Ether', sender=trader)
    assert dDAI.getRate() == 1.5*10**18, "rate is not correct"
    assert dFRAX.getRate() == 10**18, "rate is not correct"
    assert dGHO.getRate() == 10**18, "rate is not correct"

    #Swap 200 dUSD for dDAI
    struct_fund_management = (
        trader, #address sender
        False, #bool fromInternalBalance
        trader, #address payable recipient
        False #bool toInternalBalance
    )    
    struct_single_swap = (
        dUSD_pool_id, #bytes32 poolId
        0, #SwapKind.GIVEN_IN
        dUSD, #IAsset assetIn
        dDAI, #IAsset assetOut
        "200 Ether", #uint256 amount
        b"" #bytes userData
    )
    vault.swap(
        struct_single_swap, #SingleSwap singleSwap
        struct_fund_management, #FundManagement funds
        "140 Ether", #uint256 limit
        999999999999999999, #uint256 deadline
        sender=trader
    )
    bal = tokendiff(trader, tokens, bal)
    #Swap 148 dDAI for DAI
    struct_single_swap = (
        dDAI.getPoolId(), #bytes32 poolId
        0, #SwapKind.GIVEN_IN
        dDAI, #IAsset assetIn
        dai, #IAsset assetOut
        "148 Ether", #uint256 amount
        b"" #bytes userData
    )
    vault.swap(
        struct_single_swap, #SingleSwap singleSwap
        struct_fund_management, #FundManagement funds
        "200 Ether", #uint256 limit
        999999999999999999, #uint256 deadline
        sender=trader
    )
    bal = tokendiff(trader, tokens, bal)

    #Trader gets back 222 DAI from initial investment of 200 DAI

    #Batch swap to go from DAI --> dUSD
    #Swapping 500 DAI --> dDAI --> dUSD

    vault.batchSwap(
        0, #SwapKind.GIVEN_IN
        [
            (
                dDAI.getPoolId(), #poolId
                0, #assetInIndex = DAI
                1, #assetOutIndex = dDAI
                500*10**18, #amount
                b"" #bytes userData
            ),(
                dUSD_pool_id,
                1, #assetInIndex = dDAI
                2, #assetOutIndex = dUSD
                0, #amount: 0 means use whatever we got from previous step
                b"" #bytes userData
            )
        ], #BatchSwapStep[] swaps
        [
            dai,
            dDAI,
            dUSD
        ], #assets: An array of tokens which are used in the batch swap
        (
            trader, #address sender
            False, #bool fromInternalBalance
            trader, #address payable recipient
            False #bool toInternalBalance
        ), #funds
        [
            10**25,
            0,
            10**25
        ], #limits: I dont understand how this works
        999999999999999999, #uint256 deadline
        sender=trader
    )
    bal = tokendiff(trader, tokens, bal)

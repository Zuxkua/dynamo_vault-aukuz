import pytest

import ape
from tests.conftest import ensure_hardhat
from web3 import Web3
import requests, json
import eth_abi

DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
AAVE_LENDING_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
ADAI = "0x018008bfb33d285247A21d44E50697654f754e63"
AAVE_PAUSE_MASK = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFFFFFFFFF
#validate with aave dapp
AAVE_DAI_SUPPLY_CAP = 338000000000000000000000000

@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def trader(accounts):
    return accounts[1]

@pytest.fixture
def adai(project, deployer, trader, ensure_hardhat):
    return project.ERC20.at(ADAI)

@pytest.fixture
def lendingpool(project, ensure_hardhat):
    return project.aavePool.at(AAVE_LENDING_POOL)

@pytest.fixture
def dai(project, deployer, trader, ensure_hardhat):
    dai = project.DAI.at(DAI)
    # print("wards", dai.wards(deployer))
    #Make deployer a minter
    #background info https://mixbytes.io/blog/modify-ethereum-storage-hardhats-mainnet-fork
    #Dai contract has  minters in first slot mapping (address => uint) public wards;
    abi_encoded = eth_abi.encode(['address', 'uint256'], [deployer.address, 0])
    storage_slot = Web3.solidityKeccak(["bytes"], ["0x" + abi_encoded.hex()]).hex()

    set_storage_request = {"jsonrpc": "2.0", "method": "hardhat_setStorageAt", "id": 1,
        "params": [DAI, storage_slot, "0x" + eth_abi.encode(["uint256"], [1]).hex()]}
    print(requests.post("http://localhost:8545/", json.dumps(set_storage_request)))
    # print("wards", dai.wards(deployer))
    #make the trader rich, airdrop $1 billion
    dai.mint(trader, '10000000000 Ether', sender=deployer)
    # print(dai.balanceOf(trader))
    return project.ERC20.at(DAI)

@pytest.fixture
def aave_adapter(project, deployer, dai, ensure_hardhat):
    aa = deployer.deploy(project.aaveAdapter, AAVE_LENDING_POOL, dai, ADAI)
    #we run tests against interface
    return project.LPAdapter.at(aa)


@pytest.fixture
def aave_configurator(project, ensure_hardhat):
    return project.aavePoolConfigurator.at("0x64b761D848206f447Fe2dd461b0c635Ec39EbB27")

def test_aave_adapter(aave_adapter, trader, dai, adai, aave_configurator, ensure_hardhat, lendingpool):
    #Dont have any state...
    #we use sender=aave_adapter in view functions to troll the vault_location() method
    assert aave_adapter.totalAssets(sender=aave_adapter) == 0, "Asset balance should be 0"
    assert aave_adapter.maxWithdraw(sender=aave_adapter) == 0, "maxWithdraw should be 0"
    assert aave_adapter.maxDeposit(sender=aave_adapter) == pytest.approx(AAVE_DAI_SUPPLY_CAP - adai.totalSupply()), "maxDeposit should be MAX_UINT256"
    assert adai.balanceOf(aave_adapter) == 0, "adai balance incorrect"
    #Deposit 1000,000 DAI
    #Normally this would be delegate call from 4626 that already has the funds,
    #but here we fake it by transferring DAI first then doing a CALL
    dai.transfer(aave_adapter, "1000000 Ether", sender=trader)
    aave_adapter.deposit("1000000 Ether", sender=trader) #Anyone can call this, its intended to be delegate
    #There is no yield yet... so everything should be a million
    assert adai.balanceOf(aave_adapter) < 1000001*10**18, "adai balance incorrect"
    assert aave_adapter.totalAssets(sender=aave_adapter) < 1000001*10**18, "Asset balance should be 1000000"
    assert aave_adapter.maxWithdraw(sender=aave_adapter) < 1000001*10**18, "maxWithdraw should be 1000000"
    assert aave_adapter.maxDeposit(sender=aave_adapter) == pytest.approx(AAVE_DAI_SUPPLY_CAP  - adai.totalSupply()), "maxDeposit should be MAX_UINT256"
    # print(adai.balanceOf(aave_adapter))
    #cause aDAI to have a huge profit
    #mine 100000 blocks with an interval of 5 minute
    set_storage_request = {"jsonrpc": "2.0", "method": "hardhat_mine", "id": 1,
        "params": ["0x186a0", "0x12c"]}
    print(requests.post("http://localhost:8545/", json.dumps(set_storage_request)))
    # print(adai.balanceOf(aave_adapter))
    assert adai.balanceOf(aave_adapter) == pytest.approx(1007704413122972883649524), "adai balance incorrect"
    assert aave_adapter.totalAssets(sender=aave_adapter) == pytest.approx(1007704413122972883649524), "Asset balance should be 1000000"
    assert aave_adapter.maxWithdraw(sender=aave_adapter) == pytest.approx(1007704413122972883649524), "maxWithdraw should be 1000000"
    assert aave_adapter.maxDeposit(sender=aave_adapter) == pytest.approx(AAVE_DAI_SUPPLY_CAP  - adai.totalSupply()), "maxDeposit should be MAX_UINT256"
    #Withdraw everything
    trader_balance_pre = dai.balanceOf(trader)
    aave_adapter.withdraw(aave_adapter.totalAssets(sender=aave_adapter), trader, sender=trader)
    trader_gotten = dai.balanceOf(trader) - trader_balance_pre
    assert trader_gotten == pytest.approx(1007704413465903087954661), "trader gain balance incorrect"
    assert aave_adapter.totalAssets(sender=aave_adapter) < 10**18, "Asset balance should be 0"
    assert aave_adapter.maxWithdraw(sender=aave_adapter) < 10**18, "maxWithdraw should be 0"
    assert aave_adapter.maxDeposit(sender=aave_adapter) == pytest.approx(AAVE_DAI_SUPPLY_CAP  - adai.totalSupply()), "maxDeposit should be MAX_UINT256"
    assert adai.balanceOf(aave_adapter) < 10**18, "adai balance incorrect"
    
    paused = lendingpool.getConfiguration(dai).data & ~AAVE_PAUSE_MASK
    assert paused == 0, "aDAI should not be paused"

    #impersonate AAVE admin
    aaveEmergencyAdmin = "0xCA76Ebd8617a03126B6FB84F9b1c1A0fB71C2633"
    aaveACLManager = "0xc2aaCf6553D20d1e9d78E365AAba8032af9c85b0" #PoolAddressesProvider.getACLManager()
    impersonate_request = {"jsonrpc": "2.0", "method": "hardhat_impersonateAccount", "id": 1,
        "params": [aaveEmergencyAdmin]}
    print(requests.post("http://localhost:8545/", json.dumps(impersonate_request)))
    #Deposit a bit before pausing
    dai.transfer(aave_adapter, "100 Ether", sender=trader)
    aave_adapter.deposit("100 Ether", sender=trader)


    #Pause everything
    #fund the manager
    #The manager is a contract without payable fallback, so lets fudge the balance
    set_bal_req = {"jsonrpc": "2.0", "method": "hardhat_setBalance", "id": 1,
        "params": [aaveEmergencyAdmin, "0x1158E460913D00000"]}
    print(requests.post("http://localhost:8545/", json.dumps(set_bal_req)))

    # trader.transfer(aaveACLManager, 20 * 10**18)
    # tx = aave_configurator.setPoolPause.as_transaction(True, sender=aaveACLManager, gas=1000000)
    tx_request = {
        "jsonrpc": "2.0",
        "method": "eth_sendTransaction",
        "id": 1,
        "params": [
            {
                "from": aaveEmergencyAdmin,
                "to": "0x64b761D848206f447Fe2dd461b0c635Ec39EbB27",
                "gas": "0xF4240", # 1000000
                "gasPrice": "0x9184e72a000", # 10000000000000
                "value": "0x0", # 0
                "data": "0x7641f3d90000000000000000000000000000000000000000000000000000000000000001"
            }
        ]
    }
    print(requests.post("http://localhost:8545/", json.dumps(tx_request)))

    paused = lendingpool.getConfiguration(dai).data & ~AAVE_PAUSE_MASK
    assert paused != 0, "aDAI should be paused"
    
    
    #View functions work
    assert aave_adapter.totalAssets(sender=aave_adapter) == pytest.approx(100000256852263405719), "Asset balance should be 0"
    assert aave_adapter.maxWithdraw(sender=aave_adapter) == 0, "maxWithdraw should be 0"
    assert aave_adapter.maxDeposit(sender=aave_adapter) == 0, "maxDeposit should be zero"
    assert adai.balanceOf(aave_adapter) == pytest.approx(100000256852263405719), "adai balance incorrect"

    #Doing a deposit should revert
    dai.transfer(aave_adapter, "1000000 Ether", sender=trader)
    with ape.reverts("29"):
        #https://github.com/aave/aave-v3-core/blob/e0bfed13240adeb7f05cb6cbe5e7ce78657f0621/contracts/protocol/libraries/helpers/Errors.sol#L38
        #string public constant RESERVE_PAUSED = '29'; // 'Action cannot be performed because the reserve is paused'
        aave_adapter.deposit("1000000 Ether", sender=trader)

    #Doing a withdraw should revert
    with ape.reverts("29"):
        aave_adapter.withdraw("100 Ether", trader, sender=trader)

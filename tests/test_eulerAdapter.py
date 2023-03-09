import pytest

import ape
from tests.conftest import ensure_hardhat
from web3 import Web3
import requests, json
import eth_abi

DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
EDAI = "0xe025E3ca2bE02316033184551D4d3Aa22024D9DC"
EULER = "0x27182842E098f60e3D576794A5bFFb0777E025d3"

@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def trader(accounts):
    return accounts[1]

@pytest.fixture
def edai(project, deployer, trader, ensure_hardhat):
    project.eToken.at("0x27182842E098f60e3D576794A5bFFb0777E025d3")
    project.eToken.at("0xbb0D4bb654a21054aF95456a3B29c63e8D1F4c0a")
    project.IRMClassStable.at("0x42ec0eb1d2746A9f2739D7501C5d5608bdE9eE89")
    return project.eToken.at(EDAI)

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
def euler_adapter(project, deployer, dai, ensure_hardhat):
    ca = deployer.deploy(project.eulerAdapter, dai, EDAI, EULER)
    #we run tests against interface
    return project.LPAdapter.at(ca)

def test_euler_adapter(euler_adapter, trader, dai, edai, ensure_hardhat):
    #Dont have any state...
    assert euler_adapter.totalAssets(sender=euler_adapter) == 0, "Asset balance should be 0"
    assert euler_adapter.maxWithdraw(sender=euler_adapter) == 0, "maxWithdraw should be 0"
    assert euler_adapter.maxDeposit(sender=euler_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert edai.balanceOf(euler_adapter) == 0, "adai balance incorrect"
    #Deposit 1000,000 DAI
    #Normally this would be delegate call from 4626 that already has the funds,
    #but here we fake it by transferring DAI first then doing a CALL
    dai.transfer(euler_adapter, "10000 Ether", sender=trader)
    euler_adapter.deposit("10000 Ether", sender=trader) #Anyone can call this, its intended to be delegate
    #There is no yield yet... so everything should be a million
    assert euler_adapter.totalAssets(sender=euler_adapter) == pytest.approx(10000*10**18), "Asset balance should be 0"
    assert euler_adapter.maxWithdraw(sender=euler_adapter) == pytest.approx(10000*10**18), "maxWithdraw should be 0"
    assert euler_adapter.maxDeposit(sender=euler_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert edai.balanceOf(euler_adapter) == pytest.approx(9796693142892179130093), "eDAI balance incorrect"
    #cause eDAI to have a huge profit
    #mine 100000 blocks with an interval of 5 minute
    set_storage_request = {"jsonrpc": "2.0", "method": "hardhat_mine", "id": 1,
        "params": ["0x186a0", "0x12c"]}
    print(requests.post("http://localhost:8545/", json.dumps(set_storage_request)))
    # print(cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value)
    edai.touch(sender=trader)
    assert euler_adapter.totalAssets(sender=euler_adapter) == pytest.approx(10163588570541589660921), "Asset balance should be 0"
    assert euler_adapter.maxWithdraw(sender=euler_adapter) == pytest.approx(10163588570541589660921), "maxWithdraw should be 0"
    assert euler_adapter.maxDeposit(sender=euler_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert edai.balanceOf(euler_adapter) == pytest.approx(9796693142892179130093), "eDAI balance incorrect"

    #Withdraw everything
    trader_balance_pre = dai.balanceOf(trader)
    euler_adapter.withdraw(euler_adapter.totalAssets(sender=euler_adapter), trader, sender=trader)
    trader_gotten = dai.balanceOf(trader) - trader_balance_pre
    assert trader_gotten == pytest.approx(10163588570541589660921), "trader gain balance incorrect"
    assert euler_adapter.totalAssets(sender=euler_adapter) < (10**18)/1000, "Asset balance should be 0"
    assert euler_adapter.maxWithdraw(sender=euler_adapter) < (10**18)/1000, "maxWithdraw should be 0"
    assert euler_adapter.maxDeposit(sender=euler_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert edai.balanceOf(euler_adapter) < (10**18)/1000, "adai balance incorrect"

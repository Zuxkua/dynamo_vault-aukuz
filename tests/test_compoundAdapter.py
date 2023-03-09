import pytest

import ape
from tests.conftest import ensure_hardhat
from web3 import Web3
import requests, json
import eth_abi

DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
CDAI = "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643"

@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def trader(accounts):
    return accounts[1]

@pytest.fixture
def cdai(project, deployer, trader, ensure_hardhat):
    return project.cToken.at(CDAI)

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
def compound_adapter(project, deployer, dai, ensure_hardhat):
    ca = deployer.deploy(project.compoundAdapter, dai, CDAI)
    #we run tests against interface
    return project.LPAdapter.at(ca)

def test_compound_adapter(compound_adapter, trader, dai, cdai, ensure_hardhat):
    #Dont have any state...
    assert compound_adapter.totalAssets(sender=compound_adapter) == 0, "Asset balance should be 0"
    assert compound_adapter.maxWithdraw(sender=compound_adapter) == 0, "maxWithdraw should be 0"
    assert compound_adapter.maxDeposit(sender=compound_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert cdai.balanceOf(compound_adapter) == 0, "adai balance incorrect"
    #Deposit 1000,000 DAI
    #Normally this would be delegate call from 4626 that already has the funds,
    #but here we fake it by transferring DAI first then doing a CALL
    dai.transfer(compound_adapter, "1000000 Ether", sender=trader)
    compound_adapter.deposit("1000000 Ether", sender=trader) #Anyone can call this, its intended to be delegate
    #There is no yield yet... so everything should be a million
    assert cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value < 1000001*10**18, "adai balance incorrect"
    assert compound_adapter.totalAssets(sender=compound_adapter) < 1000001*10**18, "Asset balance should be 1000000"
    assert compound_adapter.maxWithdraw(sender=compound_adapter) < 1000001*10**18, "maxWithdraw should be 1000000"
    assert cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value > 999999*10**18, "adai balance incorrect"
    assert compound_adapter.totalAssets(sender=compound_adapter) > 999999*10**18, "Asset balance should be 1000000"
    assert compound_adapter.maxWithdraw(sender=compound_adapter) > 999999*10**18, "maxWithdraw should be 1000000"
    assert compound_adapter.maxDeposit(sender=compound_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    #cause cDAI to have a huge profit
    #mine 100000 blocks with an interval of 5 minute
    set_storage_request = {"jsonrpc": "2.0", "method": "hardhat_mine", "id": 1,
        "params": ["0x186a0", "0x12c"]}
    print(requests.post("http://localhost:8545/", json.dumps(set_storage_request)))
    # print(cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value)

    assert cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value == pytest.approx(1000495372237875489577903), "adai balance incorrect"
    assert compound_adapter.totalAssets(sender=compound_adapter) == pytest.approx(1000495372237875489577903), "Asset balance should be 1000000"
    assert compound_adapter.maxWithdraw(sender=compound_adapter) == pytest.approx(1000495372237875489577903), "maxWithdraw should be 1000000"
    assert cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value == pytest.approx(1000495372237875489577903), "adai balance incorrect"
    assert compound_adapter.totalAssets(sender=compound_adapter) == pytest.approx(1000495372237875489577903), "Asset balance should be 1000000"
    assert compound_adapter.maxWithdraw(sender=compound_adapter) == pytest.approx(1000495372237875489577903), "maxWithdraw should be 1000000"
    assert compound_adapter.maxDeposit(sender=compound_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    #Withdraw everything
    trader_balance_pre = dai.balanceOf(trader)
    compound_adapter.withdraw(cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value, trader, sender=trader)
    trader_gotten = dai.balanceOf(trader) - trader_balance_pre
    assert trader_gotten > 1000344*10**18, "trader gain balance incorrect"
    print(cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value)
    assert cdai.balanceOfUnderlying(compound_adapter, sender=trader).return_value < 10**18, "adai balance incorrect"
    assert compound_adapter.totalAssets(sender=compound_adapter) < 10**18, "Asset balance should be 1000000"
    assert compound_adapter.maxWithdraw(sender=compound_adapter) < 10**18, "maxWithdraw should be 1000000"

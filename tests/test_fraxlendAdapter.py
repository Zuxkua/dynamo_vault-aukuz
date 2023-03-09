import pytest

import ape
from tests.conftest import ensure_hardhat
from web3 import Web3
import requests, json
import eth_abi

FRAX = "0x853d955aCEf822Db058eb8505911ED77F175b99e"
BTC_FRAX_PAIR = "0x32467a5fc2d72D21E8DCe990906547A2b012f382"


@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def trader(accounts):
    return accounts[1]

@pytest.fixture
def fraxpair(project, deployer, trader, ensure_hardhat):
    return project.fraxpair.at(BTC_FRAX_PAIR)

@pytest.fixture
def frax(project, deployer, trader, ensure_hardhat):
    frax = project.ERC20.at(FRAX)
    #TODO: Ensure trader has enough FRAX
    #first storage slot: mapping (address => uint256) internal _balances; 
    abi_encoded = eth_abi.encode(['address', 'uint256'], [trader.address, 0])
    storage_slot = Web3.solidityKeccak(["bytes"], ["0x" + abi_encoded.hex()]).hex()
    set_storage_request = {"jsonrpc": "2.0", "method": "hardhat_setStorageAt", "id": 1,
        "params": [FRAX, storage_slot, "0x" + eth_abi.encode(["uint256"], [10**28]).hex()]}
    print(requests.post("http://localhost:8545/", json.dumps(set_storage_request)))
    return frax

@pytest.fixture
def fraxlend_adapter(project, deployer, frax, ensure_hardhat):
    fa = deployer.deploy(project.fraxlendAdapter, BTC_FRAX_PAIR, FRAX)
    return fa


def test_fraxlend_adapter(trader, frax, fraxpair, fraxlend_adapter, deployer, ensure_hardhat):
    assert fraxlend_adapter.totalAssets(sender=fraxlend_adapter) == 0, "Asset balance should be 0"
    assert fraxlend_adapter.maxWithdraw(sender=fraxlend_adapter) == 0, "maxWithdraw should be 0"
    assert fraxlend_adapter.maxDeposit(sender=fraxlend_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert fraxpair.balanceOf(fraxlend_adapter) == 0, "fToken balance incorrect"

    #deposit a million FRAX
    frax.transfer(fraxlend_adapter, "1000000 Ether", sender=trader)
    fraxlend_adapter.deposit("1000000 Ether", sender=trader) #Anyone can call this, its intended to be delegate

    assert fraxlend_adapter.totalAssets(sender=fraxlend_adapter) == pytest.approx(1000000*10**18), "Asset balance should be 0"
    assert fraxlend_adapter.maxWithdraw(sender=fraxlend_adapter) == pytest.approx(1000000*10**18), "maxWithdraw should be 0"
    assert fraxlend_adapter.maxDeposit(sender=fraxlend_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert fraxpair.balanceOf(fraxlend_adapter) == pytest.approx(999131280088931076622037), "fToken balance incorrect"

    # print(fraxlend_adapter.totalAssets())

    #cause FRAX to have a huge profit
    #mine 100000 blocks with an interval of 5 minute
    set_storage_request = {"jsonrpc": "2.0", "method": "hardhat_mine", "id": 1,
        "params": ["0x186a0", "0x12c"]}
    print(requests.post("http://localhost:8545/", json.dumps(set_storage_request)))
    #The ```addInterest``` function is a public implementation of _addInterest and allows 3rd parties to trigger interest accrual
    fraxpair.addInterest(sender=deployer)
    print(fraxlend_adapter.totalAssets(sender=fraxlend_adapter))
    assert fraxlend_adapter.totalAssets(sender=fraxlend_adapter) == pytest.approx(1001351128441541669087483), "Asset balance should be 0"
    assert fraxlend_adapter.maxWithdraw(sender=fraxlend_adapter) == pytest.approx(1001351128441541669087483), "maxWithdraw should be 0"
    assert fraxlend_adapter.maxDeposit(sender=fraxlend_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert fraxpair.balanceOf(fraxlend_adapter) == pytest.approx(999131280088931076622037), "fToken balance incorrect"

    trader_balance_pre = frax.balanceOf(trader)
    fraxlend_adapter.withdraw(fraxlend_adapter.totalAssets(sender=fraxlend_adapter), trader, sender=trader)
    trader_gotten = frax.balanceOf(trader) - trader_balance_pre
    assert trader_gotten == pytest.approx(1001351128541881348711843), "trader gain balance incorrect"
    assert fraxlend_adapter.totalAssets(sender=fraxlend_adapter) < 5, "Asset balance should be 0"
    assert fraxlend_adapter.maxWithdraw(sender=fraxlend_adapter) < 5, "maxWithdraw should be 0"
    assert fraxlend_adapter.maxDeposit(sender=fraxlend_adapter) == 2**256 - 1, "maxDeposit should be MAX_UINT256"
    assert frax.balanceOf(fraxlend_adapter) < 5, "adai balance incorrect"


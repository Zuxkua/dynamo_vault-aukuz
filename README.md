## Installation & Smoke Test

Create a python virtual environment to isolate your project and then execute the following:

Run a supported version of node.

```
nvm install 16.16.0
```

Signup for free [alchemy account](https://www.alchemy.com/), create a project with ETH mainnet and replace `REMOVED` with your api key.

```
make init
export WEB3_ETHEREUM_MAINNET_ALCHEMY_API_KEY="REMOVED"

### Setup your node snapshot RPC.



Make sure nothing is listening on port 8445.

```
sudo netstat -lntp | grep 8545
```

Optionally pre-launch the RPC server (which will block this shell):

```
npx hardhat   node   --fork https://eth-mainnet.alchemyapi.io/v2/$WEB3_ETHEREUM_MAINNET_ALCHEMY_API_KEY --fork-block-number 15936703
```
 
    OR

Edit the file source_me and enter your Alchemy API Key where it belongs then do:
```
git update-index --assume-unchanged source_me

source source_me
```

If you don't pre-launch the RPC server yourself ape will spin one up but it has a race condition and sometimes fails.


### Now in another shell:

ape test --network :mainnet-fork:hardhat
```

^^ This will fail 50% of the time, I'm working on fixing it.

## Test & Execution Environment 

We're using [ApeWorX](https://github.com/ApeWorX) with [PyTest](https://github.com/pytest-dev/pytest) as our development environment.

[ApeWorX Discord](https://discord.gg/apeworx)

[ApeWorX Website](https://www.apeworx.io/)

[ApeWorX Documentation](https://docs.apeworx.io/ape/stable/)

[PyTest Website](https://pytest.org)

## Project Tracking (Internal Only)
[Dynamo DeFi Github Project Board](https://github.com/orgs/BiggestLab/projects/6)

## Using upstream contracts

Refer to [test_swap.py](tests/test_swap.py) for an example on how we use deployed Balancer Vault to perform a swap.

We copy built artifacts from balancer project.

```bash
cp /path/to/balancer-v2-monorepo/pkg/vault/artifacts/contracts/Vault.sol/Vault.json ./contracts/
cp /path/to/balancer-v2-monorepo/pkg/solidity-utils/artifacts/@balancer-labs/v2-interfaces/contracts/solidity-utils/openzeppelin/IERC20.sol/IERC20.json ./contracts/
```

To run the test :-

```bash
ape test --network :mainnet-fork:hardhat tests/test_swap.py  -s
```

Doing this same thing in console would look like this.

```bash
ape console --network :mainnet-fork:hardhat
```

```
INFO: Starting 'Hardhat node' process.

In [1]: WETH  = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
   ...: BAL   = "0xba100000625a3754423978a60c9317c58a424e3D"
   ...: POOL_BAL_WETH = "0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56"
   ...: pool_BAL_WETH = "0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014"
   ...: VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"
   ...: weth = project.IERC20.at(WETH)
   ...: bal = project.IERC20.at(BAL)
   ...: vault = project.Vault.at(VAULT)

In [2]: trader = accounts.test_accounts[0]
   ...: 

In [3]: print(trader)
0x1e59ce931B4CFea3fe4B875411e280e173cB7A9C

In [4]: trader.transfer(WETH, "100 Ether")
INFO: Confirmed 0xe4764870ea5eb58704d6f2c0d2dcba39f9698ef2f758a024d2a70c8cd98bfe37 (total fees paid = 0)
Out[4]: <Receipt 0xe4764870ea5eb58704d6f2c0d2dcba39f9698ef2f758a024d2a70c8cd98bfe37>

In [5]: print("WETH", weth.balanceOf(trader))
   ...: print("BAL", bal.balanceOf(trader))
   ...: 
WETH 100000000000000000000
BAL 0

In [6]: weth.approve(VAULT, "100000 Ether", sender=trader)
   ...: 
INFO: Confirmed 0xebd5616549840c25d3924b7c3f272819b107a88fe34c8cbe16bba7637c89504c (total fees paid = 0)
Out[6]: <Receipt 0xebd5616549840c25d3924b7c3f272819b107a88fe34c8cbe16bba7637c89504c>

In [7]: struct_single_swap = (
   ...:     pool_BAL_WETH, #bytes32 poolId
   ...:     0, #SwapKind kind
   ...:     WETH, #IAsset assetIn
   ...:     BAL, #IAsset assetOut
   ...:     "1 Ether", #uint256 amount
   ...:     b"" #bytes userData
   ...: )
   ...: 
   ...: struct_fund_management = (
   ...:     trader, #address sender
   ...:     False, #bool fromInternalBalance
   ...:     trader, #address payable recipient
   ...:     False #bool toInternalBalance
   ...: )
   ...: 
   ...: vault.swap(
   ...:     struct_single_swap, #SingleSwap singleSwap
   ...:     struct_fund_management, #FundManagement funds
   ...:     "1 Ether", #uint256 limit
   ...:     999999999999999999, #uint256 deadline
   ...:     sender=trader
   ...: )
INFO: Confirmed 0x794533188466df6922825306fb7d1105cdf71225fa4fce6614a41112703e6888 (total fees paid = 0)
Out[7]: <Receipt 0x794533188466df6922825306fb7d1105cdf71225fa4fce6614a41112703e6888>

In [8]: print("WETH", weth.balanceOf(trader))
   ...: print("BAL", bal.balanceOf(trader))
   ...: 
WETH 99000000000000000000
BAL 233863765411278079176

In [9]:   
```

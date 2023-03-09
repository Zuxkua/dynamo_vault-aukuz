from web3 import Web3
from web3.contract import Contract
import eth_abi

import os
import json
from decimal import *
import webbrowser


def erc20_contract(_address: str) -> Contract:
    return web3.eth.contract(address=web3.toChecksumAddress(_address.lower()),abi=json.load(open('abis/ERC20.json')))

# Load private key and connect to RPC endpoint
rpc_endpoint =  os.environ.get("RPC_ENDPOINT")
private_key =   os.environ.get("KEY_PRIVATE")
if rpc_endpoint is None or private_key is None or private_key == "":
    print("\n[ERROR] You must set environment variables for RPC_ENDPOINT and KEY_PRIVATE\n")
    quit()
web3 = Web3(Web3.HTTPProvider(rpc_endpoint))
account = web3.eth.account.privateKeyToAccount(private_key)
address = account.address


# Token addresses
# https://etherscan.io/address/0xba100000625a3754423978a60c9317c58a424e3d
token_BAL   = "0xba100000625a3754423978a60c9317c58a424e3d".lower()

# https://etherscan.io/address/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
token_WETH  = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".lower()

erc20_BAL = erc20_contract(token_BAL)
BAL_decimals = int(erc20_BAL.functions.decimals().call())

erc20_WETH = erc20_contract(token_WETH)
WETH_decimals = int(erc20_WETH.functions.decimals().call())



print("Initial WETH balance: %s." % (erc20_WETH.functions.balanceOf(address).call()/(10**WETH_decimals)))
print("Initial BAL balance: %s." % (erc20_BAL.functions.balanceOf(address).call()/(10**BAL_decimals)))


# Define network settings
network = "hard hat"
block_explorer_url = "https://not_gonna_work.org/"
chain_id = 1 # hardhat - pretending to be Ethereum MainNet (was 31337)
gas_price = 2

# Load contract for Balancer Vault
address_vault = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"
path_abi_vault = 'abis/Vault.json'
with open(path_abi_vault) as f:
  abi_vault = json.load(f)
contract_vault = web3.eth.contract(
    address=web3.toChecksumAddress(address_vault), 
    abi=abi_vault
)

# Where are the tokens coming from/going to?
fund_settings = {
    "sender":               address,
    "recipient":            address,
    "fromInternalBalance":  False,
    "toInternalBalance":    False
}


# When should the transaction timeout?
deadline = 999999999999999999

# Pool IDs
# https://app.balancer.fi/#/ethereum/pool/0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014
pool_BAL_WETH = "0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014"
                


# Token data
token_data = {
    token_BAL:{
        "symbol":"BAL",
        "decimals":"18",
        "limit":"0"
    },
    token_WETH:{
        "symbol":"WETH",
        "decimals":"18",
        "limit":"1"
    }
}

swap = {
        "poolId":pool_BAL_WETH,
        "assetIn":token_WETH,
        "assetOut":token_BAL,
        "amount":"1"
    }

# Wrap some ETH
web3.eth.send_transaction({
  'to': "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
  'value': 100*10**18
})



print("After wrap WETH balance: %s." % (erc20_WETH.functions.balanceOf(address).call()/(10**WETH_decimals)))


# Approve the Vault & Pool to spend these tokens.
for contract_addr in ["0x5c6ee304399dbdb9c8ef030ab642b10820db8f56", "0xBA12222222228d8Ba445958a75a0704d566BF2C8" ]:
    for asset in ["assetIn", "assetOut"]:

        with open('abis/ERC20.json') as erc20abifile:
            abi_erc20 = json.load(erc20abifile)
        contract_erc20 = web3.eth.contract(
            address=web3.toChecksumAddress(swap[asset]),
            abi=abi_erc20
            )

        erc20_approve_function = contract_erc20.functions.approve(
            web3.toChecksumAddress(contract_addr),
            int(Decimal(swap["amount"]) * 10 ** Decimal((token_data[swap[asset]]["decimals"])))
            )

        try:
            gas_estimate = erc20_approve_function.estimateGas()
        except:
            gas_estimate = 100000
            print("Failed to estimate gas, attempting to send with", gas_estimate, "gas limit...")

        data = erc20_approve_function.build_transaction(
            {
                'chainId': chain_id,
                'gas': gas_estimate,
                'gasPrice': web3.to_wei(gas_price, 'gwei'),
                'nonce': web3.eth.get_transaction_count(address),
            }
        )

        signed_tx = web3.eth.account.sign_transaction(data, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()



# Now do the swap!

# SwapKind is an Enum. This example handles a GIVEN_IN swap.
# https://github.com/balancer-labs/balancer-v2-monorepo/blob/0328ed575c1b36fb0ad61ab8ce848083543070b9/pkg/vault/contracts/interfaces/IVault.sol#L497
swap_kind = 0 #0 = GIVEN_IN, 1 = GIVEN_OUT

user_data_encoded = eth_abi.encode_abi(['uint256'], [0])

swap_struct = (
    swap["poolId"],
    swap_kind,
    web3.toChecksumAddress(swap["assetIn"]),
    web3.toChecksumAddress(swap["assetOut"]),
    int(Decimal(swap["amount"]) * 10 ** Decimal((token_data[swap["assetIn"]]["decimals"]))),
    user_data_encoded
)

fund_struct = (
    web3.toChecksumAddress(fund_settings["sender"]),
    fund_settings["fromInternalBalance"],
    web3.toChecksumAddress(fund_settings["recipient"]),
    fund_settings["toInternalBalance"]
)

token_limit = int(Decimal(token_data[swap["assetIn"]]["limit"]) * 10 ** Decimal(token_data[swap["assetIn"]]["decimals"]))

single_swap_function = contract_vault.functions.swap(   
    swap_struct,
    fund_struct,
    token_limit,
    deadline
)

try:
    gas_estimate = single_swap_function.estimateGas()
except:
    gas_estimate = 1000000
    print("Failed to estimate gas, attempting to send with", gas_estimate, "gas limit...")

data = single_swap_function.build_transaction(
    {
        'chainId': chain_id,
        'gas': gas_estimate,
        'gasPrice': web3.to_wei(gas_price, 'gwei'),
        'nonce': web3.eth.get_transaction_count(address),
    }
)

signed_tx = web3.eth.account.sign_transaction(data, private_key)
tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
print("Sending transaction...")
#url = block_explorer_url + "tx/" + tx_hash
#webbrowser.open_new_tab(url)

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

print("Final BAL balance: %s." % (erc20_BAL.functions.balanceOf(address).call()/(10**BAL_decimals)))
print("Final WETH balance: %s." % (erc20_WETH.functions.balanceOf(address).call()/(10**WETH_decimals)))
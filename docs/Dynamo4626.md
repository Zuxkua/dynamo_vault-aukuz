# Dynamo Defi - Dynamo4626 Use Cases

## Overall Architecture

Legend for Architecture Diagram Below:

Red letters are contract addresses.
Bold black items are actual ERC20/Pool assets.
Blue zone is Vyper contract code.
    The dotted line LPAdapters are logical contracts but likely will 
    just be code in the larger AssetManager contract code base which forward requests to
    deployments of Lending Platform Specific Adapters.
Green zones are Balancer Linear Pools which will require small amounts
    of Solidity code to construct properly.
Yellow zone is the Balancer Boosted Pool which will require some Solidity
    code to fully implement/integrate.
At the bottom outside the yellow zone are the various Lending Platforms.
![Dynamo Architecture](dUSDdiagram.png "Dynamo Architecture")

## Use Cases for Dynamo4626 Contracts

The Dynamo4626 Contracts will act as AssetManagers for the Balancer LinearPools but can be treated as
their own Vaults/Pools outside of the deployed Balancer Vault.

*Given:*

Governance = address variable - Governance contract responsible for this Vault.

Being ERC-4626 Contracts, they expose the full [ERC-20 ABI](https://eips.ethereum.org/EIPS/eip-20).

### Dynamo4626 Transactional Use Cases

Definitions:

asset - underlying token by which value transactions are ultimately denominated.
        For DynamoUSD this would be one of DAI, FRAX, or GHO initially.

shares - the 4626 token representing the investment of liquidity to ultimately be converted back into assets.
        For DynamoUSD this would be dDAI, dFRAX, dGHO, and dUSD.

destination - the address of the contract or wallet to receive the value of the transaction.

owner   - the address of the contract that holds the assets in question.

Transfer - struct for transaction definition containing a signed qty and Adapter addr.
#### [deposit (assets, destination) -> shares]

Deposit fixed number of X assets for destination to receive Y shares representing the new investment.
Shares will be credited to destination address. 
```mermaid
sequenceDiagram
    participant u as Investor
    participant a4626 as d<Token>4626
    participant lpa as LP Adapter
    participant asset as <ERC20 Asset Token><br>"asset"
    #participant lp as LP
    #participant share as <ERC20 LP Share>
    participant eth as Ethereum Mainnet
  
    autonumber
    u->>a4626:deposit(assets = 500, dest = Investor)

        note over a4626, asset: We must first move the funds into the contract's balance so _getBalanceTxs will know how to best re-adjust.     
        a4626->>asset: transferFrom(from=Investor, to=a4626, amt=500)

        Note over asset: balanceOf[Investor]-=500<br>balanceOf[d<Token>4626]+=500
        asset->>a4626: amt=500
      
        Note over a4626: Compute most efficient rebalancing limited to only 2 transactions.<br>Txs = _getBalanceTxs(maxTx=2)
        a4626-->>a4626: _getBalanceTxs(maxTxs=2) -> Transfer[]
        
        a4626->lpa: _balanceAdapters

        loop for Tx: Transfer in Txs<br>(limited to maxTxs iterations)
            alt if Tx.Qty==0
                note over a4626: break
            else if Tx.Qty > 0
                a4626->>lpa: (Tx.Adapter).deposit(Tx.Qty)
                    note over lpa: asset.balanceOf[d<Token>4626]-=Tx.Qty<br>asset.balanceOf[LP]+=Tx.Qty<br>share.balanceOf[d<Token>4626]+=~Tx.Qty
                      
            else (elif Tx.Qty < 0)
                a4626->>lpa: (Tx.Adapter).withdraw(<br>asset_amount=-1 * Tx.Qty,<br>withdraw_to=d<Token>4626)
                    note over lpa: asset.balanceOf[LP]-=~Tx.Qty<br>share.balanceOf[d<Token>4626]-=~Tx.Qty<br>asset.balanceOf[d<Token>4626]+=Tx.Qty
            end
        end
      
        a4626->a4626: Shares = mintTo(dest=Investor, amt=500)
            note over a4626:d<Token>4626.balanceOf[Investor]+=500
      
        a4626->u: return Shares  
```
#### [mint (shares, destination) -> assets]

Deposit X assets where X is determined to be the quantity required to receive Y shares representing the new investment.  
Shares will be credited to destination address. For DynamoUSD this would be the LinearPool which this
contract is an AssetManager for.

#### [redeem (shares, destination, owner) -> assets]

Convert X shares controlled by owner back to Y assets to be credited to destination.
```mermaid
sequenceDiagram
    participant u as Investor
    participant a4626 as d<Token>4626
    participant lpa as LP Adapter
    participant asset as <ERC20 Asset Token><br>"asset"
    #participant lp as LP
    #participant share as <ERC20 LP Share>
    participant eth as Ethereum Mainnet
  
    autonumber
    u->>a4626:redeem(shares = 500, dest = Investor)
    note over a4626: Assets, Txs = _genRedeemTxs(shares=500)<br>Redeemed: uint256 = 0

    a4626-->>a4626: _genRedeemTxs(shares=500) -> (AssetValue, Transfer[])
    loop for Tx: Transfer in Txs
       alt if Tx.Qty==0
           note over a4626: break
       else if Tx.Qty > 0
           note over a4626: SendVal: uint256 = min(Tx.Qty, Assets-Redeemed)
           alt if SendVal > 0
               a4626->>lpa: (Tx.Adapter).withdraw(SendVal, Investor)
               note over lpa: asset.balanceOf[Investor]+=Sendval
               note over a4626: Redeemed += SendVal<br>Tx.Qty -= SendVal
           end
           alt if Tx.Qty > StrategyMinTxValue
               a4626->>lpa: (Tx.Adapter).withdraw(Tx.Qty, d<Token>4626)
               note over lpa: asset.balanceOf[d<Token>4626]+=Tx.Qty
           end
           a4626->>lpa: (Tx.Adapter).deposit(Tx.Qty)
           note over lpa: asset.balanceOf[d<Token>4626]-=Tx.Qty<br>asset.balanceOf[LP]+=Tx.Qty<br>share.balanceOf[d<Token>4626]+=~Tx.Qty
       else (otherwise)
           a4626->>lpa: (Tx.Adapter).deposit(-1 * Tx.Qty)
            note over lpa: asset.balanceOf[d<Token>4626]-=Tx.Qty<br>asset.balanceOf[LP]+=Tx.Qty<br>share.balanceOf[d<Token>4626]+=~Tx.Qty
       end    
    end
  
    alt if Assets - Redeemed > 0
        a4626->>asset: transfer(to=Investor, Assets - Redeemed)
    end
  
    a4626-->>a4626: ERC20(self).burnFrom(from=Investor, qty=shares)
   
   a4626->>u: return Assets
```
#### [withdraw (assets, destination, owner) -> shares]

Convert X shares controlled by owner where X is determined to be the quantity required to receive Y assets 
(to be credited to destination) resulting from the share value of the investment.

```mermaid
sequenceDiagram
    participant i as Investor
    participant d as d(Token)4626
    participant lp as LP Adapter
    participant erc20 as (ERC20 Asset Token) "Asset"
    participant eth as Ethereum Mainnet

    i->>d: withdraw(asset=500, dest=investor)

    d->>d: self._convertToShares(_asset_amount) -> sharesPerAsset
    note over d: if ratio 1:1 then shares=500
    
    d->>d: self.balanceOf[_owner] >= shares
    note over d: Owner has adequate shares to withdraw?
    
    d->>d: if msg.sender != _owner
    note over d: Withdrawal is handled by someone other than the owner?
    
    d->>d: ERC20(self).burnFrom(from=Investor, qty=shares)
    note over d: Burn the shares: qty=500 then shares=0
    
    d->>eth: emit event Transfer(_owner, empty(address), shares)
    note over d, eth: owner=sender, receiver=empty(address), shares=0
    
    d->>lp: self._balanceAdapters( _asset_amount )
    note over d, lp: Make sure we have enough assets to send to _receiver, asset=500
    
    lp->>lp: self._getBalanceTxs( _target_asset_balance, _max_txs )
    note over lp: Make sure we have enough assets to send to _receiver, asset=500
    
    lp->>d: self._adapter_withdraw(dtx.Adapter, qty, self)
    note over lp, d: Liquidate funds from lending pool's adapter, asset=500
    
    d->>d: ERC20(derc20asset).balanceOf(self) >= _asset_amount
    note over d: check if 4626 has enough asset to be withdrawn: _asset_amount=500 
    
    d->>i: ERC20(derc20asset).transfer(_receiver, _asset_amount)
    note over d, i: return: _receiver=investor, _asset_amount=500
```

### Dynamo4626 Supporting Functions

There may be matching preview* and max* functions for each of the deposit/mint/redeem/withdraw functions.
These simply provide read-only outcome 'previews' or maximum values possible given current balances respectively.
### Dynamo4626 Configuration/Deployment Use Cases

#### [activateStrategy()]

Checks to see if the Governance contract has a new strategy ready to activate. 
If so, makes it the new current strategy then calls rebalance to put it into effect.
This function may be called by anyone.

#### [rebalance(max_gas = 0)]

Compares the current cash & asset values across the lending platforms, computes an
optimum set of transactions necessary to best meet the current Strategy's desired 
balances, then proceeds to move assets across the lending platforms to best meet the
current strategy without exceeding the max_gas limits. If max_gas == 0 then will perform
required transactions up til the gas limits of the block.
This function may be called by anyone.
## Use Cases for Dynamo4626 Lending Platform Adapters

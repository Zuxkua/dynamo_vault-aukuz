from dataclasses import dataclass


MAX_POOLS = 5

int128 = int
uint256 = int
uint8 = int 

#@dataclass
class PoolAdapter:
    pass

@dataclass
class BalanceTX:
    Qty: int
    Adapter: PoolAdapter

    def str(self) -> str:
        return "Qty:%s, Adapter:%s" % (self.Qty, self.Adapter.self)


@dataclass
class ERC20:
    _balanceOf: dict
    def deposit(self, addr, amt):
        val = self._balanceOf.get(addr,0)
        self._balanceOf[addr] = val+amt

    def balanceOf(self, addr) -> int:
        return self._balanceOf.get(addr,0)



@dataclass
class Pool:
    dlending_pools : list[PoolAdapter] 
    derc20asset : ERC20
    strategy : list[uint256]

    def __eq__(self, other) -> bool:
        return self == other.self

    def __hash__(self) -> int:
        return hash(42)

    def getBalanceTxs( self, _target_asset_balance: uint256, _max_txs: uint8) -> list[BalanceTX]:
        # TODO: VERY INCOMPLETE

        # result : DynArray[BalanceTX, MAX_POOLS] = empty(DynArray[BalanceTX, MAX_POOLS])
        # result : BalanceTX[MAX_POOLS] = list[BalanceTX]
        result : list[BalanceTX] = [BalanceTX(Qty=0,Adapter=None) for x in range(_max_txs)]

        # If there are no pools then nothing to do.
        if len(self.dlending_pools) == 0: return result

        total_balance : uint256 = self.derc20asset.balanceOf(self) # + sum([self.derc20asset.balanceOf(pool) for pool in self.dlending_pools])
        # available_balance = total_balance - _target_asset_balance
        total_shares : uint256 = 0 #sum(self.strategy)
        targetBalances : list[uint256] = [0 for x in range(MAX_POOLS)]
        currentBalances : list[uint256] = [0 for x in range(MAX_POOLS)]
        deltaBalances : list[uint256] = [0 for x in range(MAX_POOLS)]
        #sum_in : int128 = 0 
        #sum_out: int128  = 0

        # Determine current balances.
        for pos, pool in enumerate(self.dlending_pools):            
            poolBalance : uint256 = uint256(self.derc20asset.balanceOf(pool))
            total_balance += poolBalance
            total_shares += self.strategy[pos]
            currentBalances[pos] = poolBalance
            
        available_balance : int128 = total_balance - _target_asset_balance

        # Determine target balances. 
        for pos, pool in enumerate(self.dlending_pools):               
            targetBalances[pos] = int((self.strategy[pos]/total_shares) * available_balance)
            deltaBalances[pos] = int(targetBalances[pos] - currentBalances[pos])
            #if deltaBalances[pos] > 0:
            #    sum_out += deltaBalances[pos]
            #else:
            #    sum_in += deltaBalances[pos]

        
        leftover_balance : int128 = available_balance - (sum(currentBalances) + sum(deltaBalances))
        deltaTarget : int128 = self.derc20asset.balanceOf(self) - _target_asset_balance 

        print("\nPool Adapters: %s." % self.dlending_pools)
        print("total_balance = %s." % total_balance)            
        print("targetBalances = %s." % targetBalances)
        print("currentBalances = %s." % currentBalances)
        print("deltaBalances = %s." % deltaBalances)
        print("leftover_balance = %s." % leftover_balance)
        print("_target_asset_balance = %s." % _target_asset_balance)
        print("deltaTarget = %s." % deltaTarget)
        #print("sum_in = %s." % sum_in)
        #print("sum_out = %s." % sum_out)

        tx : uint256 = 0
        for i in range(len(self.dlending_pools)):
            if deltaTarget < 0:
                lowest : int128 = 0
                lowest_pos : uint256 = 0
                for pos in range(len(self.dlending_pools)):
                    # Need to bring funds into the pool now.
                    if deltaBalances[pos] < lowest:
                        lowest = deltaBalances[pos]
                        lowest_pos = pos
                result[tx] = BalanceTX(Qty = lowest, Adapter=self.dlending_pools[lowest_pos])
                deltaBalances[lowest_pos] = 0
                deltaTarget -= lowest
                tx+=1
                continue
            else:
                largest : int128 = 0
                largest_pos : uint256 = 0                
                for pos in range(len(self.dlending_pools)):
                    # Now try for the largest abs(tx).
                    if abs(deltaBalances[pos]) > abs(largest):
                        # Make sure we don't pull below our target.
                        if deltaTarget + deltaBalances[pos] < 0: continue
                        largest = deltaBalances[pos]
                        largest_pos = pos
                result[tx] = BalanceTX(Qty = largest, Adapter=self.dlending_pools[largest_pos])
                deltaBalances[largest_pos] = 0
                deltaTarget += largest
                tx+=1
                continue

        # This likely never can be called.
        # for i in range(len(self.dlending_pools)):
        #     for pos in range(len(self.dlending_pools)):
        #         if deltaBalances[pos] != 0:
        #             result[tx] = BalanceTX(Qty = deltaBalances[pos], Adapter=self.dlending_pools[pos])
        #             tx+=1

        # Make sure we meet our _target_asset_balance goal within _max_txs steps!
        running_balance : uint256 = self.derc20asset.balanceOf(self)
        for pos in range(_max_txs):
            running_balance -= result[pos].Qty

        if running_balance < _target_asset_balance:
            print("Running short! Adjust!")
            diff : int = _target_asset_balance - running_balance
            for pos in range(_max_txs):
                available_funds = self.derc20asset.balanceOf(result[pos].Adapter) + result[pos].Qty
                if available_funds >= diff:
                    result[pos].Qty-=diff
                    diff=0
                    break
                elif available_funds > 0:
                    result[pos].Qty-=available_funds
                    diff+=available_funds

            assert diff <= 0, "CAN'T BALANCE IN %s STEP!" % _max_txs

        if len(result) > _max_txs:
            for pos in range(len(result)-_max_txs):
                result[pos+_max_txs]=BalanceTX(Qty=0,Adapter=PoolAdapter())

        # DEBUGGING ONLY
        running_balance : int = self.derc20asset.balanceOf(self)                
        for tx in result:
            if tx.Adapter == None: break
            running_balance -= tx.Qty
            adapt_pos = self.dlending_pools.index(tx.Adapter)
            print("Adapter:%s target balance: %s, final balance: %s." % (tx.Adapter,targetBalances[adapt_pos],currentBalances[adapt_pos]+tx.Qty))
        print("Pool target balance: %s, final balance: %s." % (_target_asset_balance,running_balance))            

        return result


d = {}
dai = ERC20(_balanceOf = d)

a1 = PoolAdapter()
a2 = PoolAdapter()

adapters = [a1,a2]

p = Pool(adapters, dai, [0 for x in range(MAX_POOLS)])
p.strategy[0] = 50
p.strategy[1] = 50

dai.deposit(a1, 20)

dai.deposit(p,500) 


result = p.getBalanceTxs(0, 5)

print(result)

result = p.getBalanceTxs(250, 5)

print(result)

dai.deposit(a2, 600)

result = p.getBalanceTxs(545, 5)

print(result)
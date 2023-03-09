# @version 0.3.7

event StrategyWithdrawal:
    Nonce: uint256

event StrategyVote:
    Nonce: uint256
    GuardAddress: indexed(address)
    Endorse: bool

event StrategyActivation:
    strategy: Strategy

event NewGuard:
    GuardAddress: indexed(address)

event GuardRemoved:
    GuardAddress: indexed(address)

event GuardSwap:
    OldGuardAddress: indexed(address)
    NewGuardAddress: indexed(address)

event GovernanceContractChanged:
    Vault: address
    Voter: address
    NewGovernance: indexed(address)
    VoteCount: uint256
    TotalGuards: uint256

event VoteForNewGovernance:
    NewGovernance: indexed(address)
    
struct ProposedStrategy:
    Weights: DynArray[uint256, MAX_POOLS]
    APYNow: uint256
    APYPredicted: uint256

struct Strategy:
    Nonce: uint256
    ProposerAddress: address
    Weights: DynArray[uint256, MAX_POOLS]
    APYNow: uint256
    APYPredicted: uint256
    TSubmitted: uint256
    TActivated: uint256
    Withdrawn: bool
    no_guards: uint256
    VotesEndorse: DynArray[address, MAX_GUARDS]
    VotesReject: DynArray[address, MAX_GUARDS]

event StrategyProposal:
    strategy: Strategy
    
# Contract assigned storage 
contractOwner: public(address)
MAX_GUARDS: constant(uint256) = 2
MAX_POOLS: constant(uint256) = 10
LGov: public(DynArray[address, MAX_GUARDS])
TDelay: public(uint256)
no_guards: public(uint256)
CurrentStrategy: public(Strategy)
PendingStrategy: public(Strategy)
VotesGC: public(HashMap[address, address])
MIN_GUARDS: constant(uint256) = 1
NextNonce: uint256

Vault: public(address)

interface Vault:
    def PoolRebalancer(currentStrategy: Strategy) -> bool: nonpayable
    def replaceGovernanceContract(NewGovernance: address) -> bool: nonpayable


@external
def __init__(contractOwner: address, _vault: address, _tdelay: uint256):
    self.contractOwner = contractOwner
    self.Vault = _vault
    self.NextNonce = 1
    self.TDelay = _tdelay
    if _tdelay == empty(uint256):
        self.TDelay = 21600


@external
def submitStrategy(strategy: ProposedStrategy) -> uint256:
    # No Strategy proposals if no governance guards
    assert len(self.LGov) > 0, "Cannot Submit Strategy without Guards"

    # Confirm there's no currently pending strategy so we can replace the old one.

            # First is it the same as the current one?
            # Otherwise has it been withdrawn? 
            # Otherwise, has it been short circuited down voted? 
            # Has the period of protection from being replaced expired already?         
    assert  (self.CurrentStrategy.Nonce == self.PendingStrategy.Nonce) or \
            (self.PendingStrategy.Withdrawn == True) or \
            len(self.PendingStrategy.VotesReject) > 0 and \
            (len(self.PendingStrategy.VotesReject) >= self.PendingStrategy.no_guards/2) or \
            (convert(block.timestamp, decimal) > (convert(self.PendingStrategy.TSubmitted, decimal)+(convert(self.TDelay, decimal) * 1.25)))

    # Confirm msg.sender Eligibility
    # Confirm msg.sender is not blacklisted

    # Confirm strategy meets financial goal improvements.
    assert strategy.APYPredicted - strategy.APYNow > 0, "Cannot Submit Strategy without APY Increase"

    self.PendingStrategy.Nonce = self.NextNonce
    self.NextNonce += 1
    self.PendingStrategy.ProposerAddress = msg.sender
    self.PendingStrategy.Weights = strategy.Weights
    self.PendingStrategy.APYNow = strategy.APYNow
    self.PendingStrategy.APYPredicted = strategy.APYPredicted
    self.PendingStrategy.TSubmitted = block.timestamp
    self.PendingStrategy.TActivated = 0    
    self.PendingStrategy.Withdrawn = False
    self.PendingStrategy.no_guards = len(self.LGov)
    self.PendingStrategy.VotesEndorse = empty(DynArray[address, MAX_GUARDS])
    self.PendingStrategy.VotesReject = empty(DynArray[address, MAX_GUARDS])

    log StrategyProposal(self.PendingStrategy)
    return self.PendingStrategy.Nonce


@external
def withdrawStrategy(Nonce: uint256):
    #Check to see that the pending strategy is not the current strategy
    assert (self.CurrentStrategy.Nonce != self.PendingStrategy.Nonce), "Cannot withdraw Current Strategy"

    #Check to see that the pending strategy's nonce matches the nonce we want to withdraw
    assert self.PendingStrategy.Nonce == Nonce, "Cannot Withdraw Strategy if its not Pending Strategy"

    #Check to see that sender is eligible to withdraw
    assert self.PendingStrategy.ProposerAddress == msg.sender

    #Withdraw Pending Strategy
    self.PendingStrategy.Withdrawn = True

    log StrategyWithdrawal(Nonce)


@external
def endorseStrategy(Nonce: uint256):
    #Check to see that the pending strategy is not the current strategy
    assert self.CurrentStrategy.Nonce != self.PendingStrategy.Nonce, "Cannot Endorse Strategy thats already  Strategy"

    #Check to see that the pending strategy's nonce matches the nonce we want to endorse
    assert self.PendingStrategy.Nonce == Nonce, "Cannot Endorse Strategy if its not Pending Strategy"

    #Check to see that sender is eligible to vote
    assert msg.sender in self.LGov, "Sender is not eligible to vote"

    #Check to see that sender has not already voted
    assert msg.sender not in self.PendingStrategy.VotesReject
    assert msg.sender not in self.PendingStrategy.VotesEndorse

    #Vote to endorse strategy
    self.PendingStrategy.VotesEndorse.append(msg.sender)

    log StrategyVote(Nonce, msg.sender, False)


@external
def rejectStrategy(Nonce: uint256):
    #Check to see that the pending strategy is not the current strategy
    assert self.CurrentStrategy.Nonce != self.PendingStrategy.Nonce, "Cannot Reject Strategy thats already Current Strategy"

    #Check to see that the pending strategy's nonce matches the nonce we want to reject
    assert self.PendingStrategy.Nonce == Nonce, "Cannot Reject Strategy if its not Pending Strategy"

    #Check to see that sender is eligible to vote
    assert msg.sender in self.LGov

    #Check to see that sender has not already voted
    assert msg.sender not in self.PendingStrategy.VotesReject
    assert msg.sender not in self.PendingStrategy.VotesEndorse

    #Vote to reject strategy
    self.PendingStrategy.VotesReject.append(msg.sender)

    log StrategyVote(Nonce, msg.sender, True)


@external
def activateStrategy(Nonce: uint256):
    #Confirm there is a currently pending strategy
    assert (self.CurrentStrategy.Nonce != self.PendingStrategy.Nonce)
    assert (self.PendingStrategy.Withdrawn == False)

    #Confirm strategy is approved by guards
    assert (len(self.PendingStrategy.VotesEndorse) >= len(self.LGov)/2) or \
           ((self.PendingStrategy.TSubmitted + self.TDelay) < block.timestamp)
    assert len(self.PendingStrategy.VotesReject) < len(self.PendingStrategy.VotesEndorse)

    #Confirm Pending Strategy is the Strategy we want to activate
    assert self.PendingStrategy.Nonce == Nonce

    #Make Current Strategy and Activate Strategy
    self.CurrentStrategy = self.PendingStrategy
    # Vault(self.Vault).PoolRebalancer(self.CurrentStrategy)

    log StrategyActivation(self.CurrentStrategy)
 

@external
def addGuard(GuardAddress: address):
    #Check to see that sender is the contract owner
    assert msg.sender == self.contractOwner, "Cannot add guard unless you are contract owner"

    #Check to see if there is the max amount of Guards
    assert len(self.LGov) <= MAX_GUARDS, "Cannot add anymore guards"

    #Check to see that the Guard being added is a valid address
    assert GuardAddress != ZERO_ADDRESS, "Cannot add ZERO_ADDRESS"

    #Check to see that GuardAddress is not already in self.LGov
    assert GuardAddress not in self.LGov, "Guard already exists"

    #Add new guard address as the last in the list of guards
    self.LGov.append(GuardAddress)

    log NewGuard(GuardAddress)


@external
def removeGuard(GuardAddress: address):
    #Check to see that sender is the contract owner
    assert msg.sender == self.contractOwner, "Cannot remove guard unless you are contract owner"

    last_index: uint256 = len(self.LGov) 
    #Check to see if there are any guards on the list of guards
    assert last_index != 0, "No guards to remove."

    # Correct size to zero offset position.
    last_index -= 1
    
    #Run through list of guards to find the index of the one we want to remove
    current_index: uint256 = 0
    for guard_addr in self.LGov:
        if guard_addr == GuardAddress: break
        current_index += 1

    #Make sure that GuardAddress is a guard on the list of guards
    assert GuardAddress == self.LGov[current_index], "GuardAddress not a current Guard."    

    # Replace Current Guard with last
    self.LGov[current_index] = self.LGov[last_index]

    # Eliminate the redundant one at the end.
    self.LGov.pop()

    log GuardRemoved(GuardAddress)


@external
def swapGuard(OldGuardAddress: address, NewGuardAddress: address):
    #Check that the sender is authorized to swap a guard
    assert msg.sender == self.contractOwner, "Cannot swap guard unless you are contract owner"

    #Check that the guard we are swapping in is a valid address
    assert NewGuardAddress != ZERO_ADDRESS, "Cannot add ZERO_ADDRESS"

    #Check that the guard we are swapping in is not on the list of guards already
    assert NewGuardAddress not in self.LGov, "New Guard is already a Guard."

    #Run through list of guards to find the index of the one we want to swap out
    current_index: uint256 = 0 
    for guard_addr in self.LGov:
        if guard_addr == OldGuardAddress: break
        current_index += 1

    #Make sure that OldGuardAddress is a guard on the list of guards
    assert OldGuardAddress == self.LGov[current_index], "OldGuardAddress not a current Guard."

    #Replace OldGuardAddress with NewGuardAddress
    self.LGov[current_index] = NewGuardAddress

    log GuardSwap(OldGuardAddress, NewGuardAddress)


@external
def replaceGovernance(NewGovernance: address):
    VoteCount: uint256 = 0
    Voter: address = msg.sender
    TotalGuards: uint256 = len(self.LGov)
    #Check if there are enough guards to change governance
    assert len(self.LGov) >= MIN_GUARDS

    #Check if sender is a guard
    assert msg.sender in self.LGov

    #Check if new contract address is not the current)
    assert NewGovernance != self

    #Check if new contract address is valid address
    assert NewGovernance != ZERO_ADDRESS

    #Check if sender has voted, if not log new vote
    if self.VotesGC[msg.sender] != NewGovernance: 
        log VoteForNewGovernance(NewGovernance)

    #Record Vote
    self.VotesGC[msg.sender] = NewGovernance

    #Add Vote to VoteCount
    for guard_addr in self.LGov:
        if self.VotesGC[guard_addr] == NewGovernance:
            VoteCount += 1

    # if len(self.LGov) == VoteCount:
    #     Vault(self.Vault).replaceGovernanceContract(NewGovernance)

    log GovernanceContractChanged(self.Vault, Voter, NewGovernance, VoteCount, TotalGuards)


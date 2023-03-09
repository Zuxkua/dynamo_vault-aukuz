import time
from datetime import datetime, timedelta

import ape

import pytest
from  pytest import raises

WEIGHTS = [100, 1000]
APYNOW = 5
APYPREDICTED = 10
BADAPYPREDICTED = 3
NONCE = 1
VOTE_COUNT = 6
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def vault_contract(owner, project, accounts):

    owner, operator, someoneelse, someone, newcontract, currentvault, currentgovernance = accounts[:7]

    vcontract = owner.deploy(project.Vault_test, owner)

    return vcontract

@pytest.fixture
def governance_contract(owner, project, accounts, vault_contract):

    owner, operator, someoneelse, someone, newcontract, currentvault = accounts[:6]

    # deploy the contract with the initial value as a constructor argument

    gcontract = owner.deploy(project.Governance, owner, vault_contract, 21600)

    return gcontract  


def test_submitStrategy(governance_contract, accounts, owner):
    ProposedStrategy = (WEIGHTS, APYNOW, APYPREDICTED)
    BadStrategy = (WEIGHTS, APYNOW, BADAPYPREDICTED)
    owner, operator, someoneelse, someone = accounts[:4]

    #Test if i can submit strategy with zero guards
    with ape.reverts():
        governance_contract.submitStrategy(ProposedStrategy, sender=owner)

    #Add a guard
    governance_contract.addGuard(someone, sender=owner)

    print("Current timestamp %s" % datetime.fromtimestamp(ape.chain.pending_timestamp))


    #Submit a strategy
    sp = governance_contract.submitStrategy(ProposedStrategy, sender=owner)
    logs = list(sp.decode_logs(governance_contract.StrategyProposal))
    assert len(logs) == 1
    assert logs[0].strategy[2] == tuple(WEIGHTS)
    assert logs[0].strategy[3] == APYNOW
    assert logs[0].strategy[4] == APYPREDICTED

    print("Current timestamp %s" % datetime.fromtimestamp(ape.chain.pending_timestamp))
    print("TDelay %s" % datetime.fromtimestamp(int(governance_contract.TDelay())) )

    tdelay = int((int(governance_contract.TDelay()) * 1.25))

    print("Expire time %s " % datetime.fromtimestamp(int(ape.chain.pending_timestamp) + tdelay) )


    governance_contract.PendingStrategy.Nonce = NONCE

    #Test if i can submit a strategy while there is pending strategy
    with ape.reverts():
        governance_contract.submitStrategy(ProposedStrategy, sender=owner)

    #Test if i can submit a strategy where the APY does not increase
    with ape.reverts():
        governance_contract.submitStrategy(BadStrategy, sender=owner)

    print("Current timestamp %s" % datetime.fromtimestamp(ape.chain.pending_timestamp))








def test_withdrawStrategy(governance_contract, accounts):
    ProposedStrategy = (WEIGHTS, APYNOW, APYPREDICTED)
    owner, operator, someoneelse, someone = accounts[:4]

    #Add a guard
    governance_contract.addGuard(someone, sender=owner)

    #Submit a strategy
    sp = governance_contract.submitStrategy(ProposedStrategy, sender=owner)
    logs = list(sp.decode_logs(governance_contract.StrategyProposal))
    assert len(logs) == 1

    #Test if i can withdraw strategy when nonce doesn't match
    with ape.reverts():
        ws = governance_contract.withdrawStrategy(2, sender=owner)

    governance_contract.PendingStrategy.Nonce = NONCE

    #Test if i can withdraw strategy when i am not eligible
    with ape.reverts():
        ws = governance_contract.withdrawStrategy(NONCE, sender=someone)

    print("Current timestamp %s" % datetime.fromtimestamp(ape.chain.pending_timestamp))

    #Withdraw Strategy
    ws = governance_contract.withdrawStrategy(NONCE, sender=owner)
    logs = list(ws.decode_logs(governance_contract.StrategyWithdrawal))
    assert len(logs) == 1
    assert logs[0].Nonce == NONCE

    current_time = datetime.fromtimestamp(ape.chain.pending_timestamp)
    print("Current timestamp %s" % current_time)
    current_time += timedelta(days=1)
    ape.chain.pending_timestamp = int(current_time.timestamp())

    #Submit a second Strategy
    sp = governance_contract.submitStrategy(ProposedStrategy, sender=owner)
    logs = list(sp.decode_logs(governance_contract.StrategyProposal))
    assert len(logs) == 1

    print("Current timestamp %s" % datetime.fromtimestamp(ape.chain.pending_timestamp))

    governance_contract.PendingStrategy.Nonce = 2

    #Endorse the strategy
    es = governance_contract.endorseStrategy(2, sender=someone)
    logs = list(es.decode_logs(governance_contract.StrategyVote))

    #Activate the startegy
    acs = governance_contract.activateStrategy(2, sender=owner)
    logs = list(acs.decode_logs(governance_contract.StrategyActivation))
    assert len(logs) == 1
    assert logs[0].strategy[2] == tuple(WEIGHTS)
    assert logs[0].strategy[3] == APYNOW
    assert logs[0].strategy[4] == APYPREDICTED

    #Test if i can withdraw strategy when its already activated
    with ape.reverts():
        governance_contract.withdrawStrategy(2, sender=owner)



def test_endorseStrategy(governance_contract, accounts):
    ProposedStrategy = (WEIGHTS, APYNOW, APYPREDICTED)
    owner, operator, someoneelse, someone = accounts[:4]

    #Add a guard
    governance_contract.addGuard(someone, sender=owner)

    #Submit a Strategy
    sp = governance_contract.submitStrategy(ProposedStrategy, sender=owner)
    logs = list(sp.decode_logs(governance_contract.StrategyProposal))
    assert len(logs) == 1

    #Test to see if we can endorse strategy when Nonce doesn't match
    with ape.reverts():
        es = governance_contract.endorseStrategy(2, sender=someone)

    governance_contract.PendingStrategy.Nonce = NONCE

    #Test to see if we can vote while not being a guard
    with ape.reverts():
        es = governance_contract.endorseStrategy(NONCE, sender=owner)

    #Vote to Endorse Strategy
    es = governance_contract.endorseStrategy(NONCE, sender=someone)
    logs = list(es.decode_logs(governance_contract.StrategyVote))
    assert len(logs) == 1
    assert logs[0].Nonce == NONCE
    assert logs[0].GuardAddress == someone
    assert logs[0].Endorse == False

    #Test to see if i can vote again
    with ape.reverts():
        es = governance_contract.endorseStrategy(NONCE, sender=someone)

    #Activate Strategy
    acs = governance_contract.activateStrategy(NONCE, sender=owner)
    logs = list(acs.decode_logs(governance_contract.StrategyActivation))
    assert len(logs) == 1

    #Add another guard
    governance_contract.addGuard(someoneelse, sender=owner)

    #Test to see if we can endorse strategy after its already activated
    with ape.reverts():
        es = governance_contract.endorseStrategy(NONCE, sender=someoneelse)

    #Test to see if we can reject strategy after its already activated
    with ape.reverts():
        rs = governance_contract.rejectStrategy(NONCE, sender=someoneelse)


def test_rejectStrategy(governance_contract, accounts):
    ProposedStrategy = (WEIGHTS, APYNOW, APYPREDICTED)
    owner, operator, someoneelse, someone = accounts[:4]

    #Add a guard
    governance_contract.addGuard(someone, sender=owner)

    #Submit a Strategy
    sp = governance_contract.submitStrategy(ProposedStrategy, sender=owner)
    logs = list(sp.decode_logs(governance_contract.StrategyProposal))
    assert len(logs) == 1

    #Test to see if we can reject strategy when Nonce doesn't match
    with ape.reverts():
        rs = governance_contract.rejectStrategy(2, sender=someone)

    governance_contract.PendingStrategy.Nonce = NONCE

    #Check to see if we can vote while not being a guard
    with ape.reverts():
        rs = governance_contract.rejectStrategy(NONCE, sender=owner)
    
    #Vote to Reject Strategy
    rs = governance_contract.rejectStrategy(NONCE, sender=someone)
    logs = list(rs.decode_logs(governance_contract.StrategyVote))
    assert len(logs) == 1
    assert logs[0].Nonce == NONCE
    assert logs[0].GuardAddress == someone
    assert logs[0].Endorse == True

    #Test to see if i can vote again
    with ape.reverts():
        rs = governance_contract.rejectStrategy(NONCE, sender=someone)



def test_activateStrategy(governance_contract, accounts):
    ProposedStrategy = (WEIGHTS, APYNOW, APYPREDICTED)
    owner, operator, someoneelse, someone = accounts[:4]

    #Add a guard
    governance_contract.addGuard(someone, sender=owner)

    #Submit a Strategy
    sp = governance_contract.submitStrategy(ProposedStrategy, sender=owner)
    logs = list(sp.decode_logs(governance_contract.StrategyProposal))
    assert len(logs) == 1

    governance_contract.PendingStrategy.Nonce = NONCE

    #Endorse the strategy
    es = governance_contract.endorseStrategy(NONCE, sender=someone)
    logs = list(es.decode_logs(governance_contract.StrategyVote))

    #Activate the startegy
    acs = governance_contract.activateStrategy(NONCE, sender=owner)
    logs = list(acs.decode_logs(governance_contract.StrategyActivation))
    assert len(logs) == 1
    assert logs[0].strategy[2] == tuple(WEIGHTS)
    assert logs[0].strategy[3] == APYNOW
    assert logs[0].strategy[4] == APYPREDICTED

    #Submit another Strategy
    governance_contract.submitStrategy(ProposedStrategy, sender=owner)

    governance_contract.PendingStrategy.Nonce = 2

    #Endorse the second strategy
    es = governance_contract.endorseStrategy(2, sender=someone)

    #Test if i can activate strategy with wrong nonce
    with ape.reverts():
        acs = governance_contract.activateStrategy(3, sender=owner)

    ws = governance_contract.withdrawStrategy(2, sender=owner)

    #Test if i can activate strategy when its withdrawn
    with ape.reverts():
        acs = governance_contract.activateStrategy(2, sender=owner)
 

def test_addGuard(governance_contract, accounts):
    owner, operator, someoneelse, someone = accounts[:4]

    #Test if i can add a guard as someone who is not the contract owner.
    with ape.reverts():
        ag = governance_contract.addGuard(someone, sender=someone)
    
    #Test if i can add guard.
    ag = governance_contract.addGuard(someone, sender=owner)
    logs = list(ag.decode_logs(governance_contract.NewGuard))
    assert len(logs) == 1
    assert logs[0].GuardAddress == someone

    #Test if i can add the same guard again.
    with ape.reverts():
        ag = governance_contract.addGuard(someone, sender=owner)

    #Test if i can add a ZERO_ADDRESS.
    with ape.reverts():
        ag = governance_contract.addGuard(ZERO_ADDRESS, sender=owner)

    ag = governance_contract.addGuard(someoneelse, sender=owner)

    #Test if i can add a guard when len(LGov) = MAX_GUARDS
    with ape.reverts():
        ag = governance_contract.addGuard(operator, sender=owner)



def test_removeGuard(governance_contract, accounts):
    owner, operator, someoneelse, someone = accounts[:4]

    #Test to see if i can remove a guard when there are no guards.
    with ape.reverts():
        rg = governance_contract.removeGuard(someone, sender=owner)

    # Now add a guard.        
    governance_contract.addGuard(someone, sender=owner)

    #Test if i can remove a guard as someone who is not the contract owner.
    with ape.reverts():
        rg = governance_contract.removeGuard(someone, sender=someone)

    #Test to see if i can remove a guard thats not in list of guards.
    with ape.reverts():
        rg = governance_contract.removeGuard(operator, sender=owner)

    #Test if i can remove a guard.
    rg = governance_contract.removeGuard(someone, sender=owner)    
    logs = list(rg.decode_logs(governance_contract.GuardRemoved))
    assert len(logs) == 1
    assert logs[0].GuardAddress == someone


def test_swapGuard(governance_contract, accounts):
    owner, operator, someoneelse, someone = accounts[:4]

    #Test if i can swap out a guard that is not on the list of guards.
    with ape.reverts():
        sg = governance_contract.swapGuard(someone, someoneelse, sender=owner)

    governance_contract.addGuard(someone, sender=owner)

    #Test if i can swap a guard as someone who is not the contract owner.
    with ape.reverts():
        sg = governance_contract.swapGuard(someone, someoneelse, sender=someoneelse)

    #Test if i can add a ZERO_ADDRESS.
    with ape.reverts():
        sg = governance_contract.swapGuard(someone, ZERO_ADDRESS, sender=owner)

    governance_contract.addGuard(operator, sender=owner)

    #Test if i can swap in a guard thats already on the list of guards.
    with ape.reverts():
        sg = governance_contract.swapGuard(someone, operator, sender=owner)

    #Test if i can swap guard.
    sg = governance_contract.swapGuard(someone, someoneelse, sender=owner)
    logs = list(sg.decode_logs(governance_contract.GuardSwap))
    assert len(logs) == 1
    assert logs[0].OldGuardAddress == someone
    assert logs[0].NewGuardAddress == someoneelse



def test_replaceGovernance(governance_contract, accounts):
    owner, operator, someoneelse, someone, newcontract = accounts[:5]

    #Test if i can replace governance when there are no guards
    with ape.reverts():
        governance_contract.replaceGovernance(newcontract, sender=owner)

    #Add a guard
    governance_contract.addGuard(someone, sender=owner)

    #Test if i can replace governance if sender is not in list of guards
    with ape.reverts():
        governance_contract.replaceGovernance(newcontract, sender=owner)

    #Test if i can replace governance with self
    with ape.reverts():
        governance_contract.replaceGovernance(governance_contract, sender=someone)

    #Test if i can replace governance with invalid address
    with ape.reverts():
        governance_contract.replaceGovernance(ZERO_ADDRESS, sender=someone)

    #Test if replace governance logs new vote
    rg = governance_contract.replaceGovernance(newcontract, sender=someone)
    logs = list(rg.decode_logs(governance_contract.VoteForNewGovernance))
    assert len(logs) == 1
    assert logs[0].NewGovernance == newcontract

    logs = list(rg.decode_logs(governance_contract.GovernanceContractChanged))
    assert len(logs) == 1
    assert logs[0].Voter == someone
    assert logs[0].NewGovernance == newcontract

    #Test if VoteCount increases correctly
    assert logs[0].VoteCount == 1
    assert logs[0].TotalGuards == 1
from negmas import NegotiatorMechanismInterface
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional


class BiddingStrategy:

    # These are the parameters to initialize our bidding strategy, helping the other two functions to make decisions.
    # We should pre sort by our utility (desc) to help get_bid() find a bid near our target utility efficiently.
    def __init__(self, negotiatorMechanism: NegotiatorMechanismInterface, utilityFunc: UtilityFunction):
        self.nmi = negotiatorMechanism
        self.uFun = utilityFunc
    # Our strategy, returning the minimum utility we are willing to bid at time t in [0, 1].
    # At t=0 we want to be ambitous, bid high and closer to deadling we want to concede more
    # Ofcourse never under our reservation value. 
    # We can use different concession curves, like Boulware (concede late), Conceder (concede early) or Linear.
    # Also more info on this in "Introduction to Automated Negotiation" by de Jonge. 
    def target_utility(self, t: float) -> float:
        pass
    
    # This is where we return the next bid we want to propse at time t.
    # Compute target utility with func above, find outcome with utility >= target and return.
    # If none exist fallback to best known outcome.
    # Another thing i saw was randomizing among near optimal outcomes makes us less predictable.
    def get_bid(self, t: float, state) -> Optional[Outcome]:
        pass
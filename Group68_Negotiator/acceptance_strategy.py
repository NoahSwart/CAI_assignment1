from negmas import NegotiatorMechanismInterface, SAOState
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction

class AcceptanceStrategy:

    # These are the parameters to initialize our acceptance strategy, helping the other two functionsto make decisions.
    def __init__(self, negotiatorMechanism: NegotiatorMechanismInterface, utilityFunc: UtilityFunction):
        self.nmi = negotiatorMechanism
        self.uFun = utilityFunc
    # Here we need to return the minimum utility we can accept at given 
    # time t (in range [0,1], where 0 is the start of the negotiation and 1 is the deadline).
    # we should decrease the acc threshold closer to deadline, but it should never go below our reservation value.
    # We need to tune this very carefully (Lookup strategies)
    def acceptance_threshold(self, t: float) -> float:
        pass
    # T -> accept offer, F -> reject offer. Our mechanism to decide whether to return T Or F.
    # We always reject offers below our reservation value.
    # Otherwise, we can use AC_next, AC_time, AC_combi or any other strategy we want to implement.
    # Saw these being used in: "Introduction to Automated Negotiation" by de Jonge.
    def should_accept(self, offer: Outcome, t: float, state: SAOState) -> bool:
        pass
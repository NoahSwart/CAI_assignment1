import math
from negmas.common import NegotiatorMechanismInterface
from negmas.sao import SAOState
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction

class AcceptanceStrategy:

    # These are the parameters to initialize our acceptance strategy, helping the other two functionsto make decisions.
    def __init__(self, negotiatorMechanism: NegotiatorMechanismInterface, utilityFunc: UtilityFunction):
        self.nmi = negotiatorMechanism
        self.uFun = utilityFunc
        self.reservation = self.uFun.reserved_value
        self.beta = 2.0  # higher = slower concession early, faster near deadline

    # Here we need to return the minimum utility we can accept at given 
    # time t (in range [0,1], where 0 is the start of the negotiation and 1 is the deadline).
    # we should decrease the acc threshold closer to deadline, but it should never go below our reservation value.
    # We use AC_time + AC_asp with a Boulware like concession curve
    def acceptance_threshold(self, t: float) -> float:
        aspiration = self.reservation + (1 - self.reservation) * (1 - math.pow(t, self.beta))
        return max(self.reservation, aspiration)

    # T -> accept offer, F -> reject offer. Our mechanism to decide whether to return T Or F.
    # We always reject offers below our reservation value.
    # We use AC_next, AC_time, AC_combi to make a hybrid.
    # Saw these being used in: "Introduction to Automated Negotiation" by de Jonge.
    def should_accept(self, offer: Outcome, t: float, state: SAOState) -> bool:
        offer_utility = self.uFun(offer)

        if offer_utility < self.reservation:
            return False

        threshold = self.acceptance_threshold(t)
        if offer_utility >= threshold:
            return True

        # Optional 1: Gradually lower threshold from 0% at the beginning to 10% near the deadline
        # tau = 1 - t
        # expected_future = threshold * (0.9 + 0.1 * tau)
        # if offer_utility >= expected_future:
        #     return True

        # Optional 2: Accept anything slightly above reservation right before the deadline
        # if t > 0.95 and offer_utility >= self.reservation + 0.25 * self.reservation:
        #     return True

        # Optional 3: Compare with best seen so far
        best_seen = max(self.uFun(state_i.current_offer) for state_i in self.nmi.history)
        if offer_utility >= best_seen:
            return True

        return False
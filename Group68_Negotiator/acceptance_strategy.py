import math
from negmas.common import NegotiatorMechanismInterface
from negmas.sao import SAOState
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional

from Group68_Negotiator.opponent_model import OpponentModel

class AcceptanceStrategy:
    # Concession speed in AC_time threshold. Higher => hold out longer for better offers.
    DEFAULT_BETA = 4.0
    # Only apply best-seen heuristic late in the negotiation.
    BEST_SEEN_LATE_STAGE = 0.90
    # Offer must improve over previous best by at least this utility margin.
    BEST_SEEN_IMPROVEMENT_MARGIN = 1.0
    # Offer must also remain close to current time-based threshold.
    BEST_SEEN_THRESHOLD_FRACTION = 0.95
    # Minimum utility lead over estimated opponent utility when using opponent-aware acceptance.
    ADVANTAGE_BASE = 0.45

    # These are the parameters to initialize our acceptance strategy, helping the other two functionsto make decisions.
    def __init__(
        self,
        negotiatorMechanism: NegotiatorMechanismInterface,
        utilityFunc: UtilityFunction,
        opponent_model: Optional[OpponentModel] = None,
    ):
        self.nmi = negotiatorMechanism
        self.uFun = utilityFunc
        self.opponent_model = opponent_model
        self.reservation = float(self.uFun.reserved_value)
        best_outcome = self.uFun.best(self.nmi.outcome_space)
        self.max_utility = float(self.uFun(best_outcome)) if best_outcome is not None else self.reservation
        self.beta = self.DEFAULT_BETA

    def _required_advantage(self, t: float) -> float:
        t = min(1.0, max(0.0, float(t)))
        advantage = self.ADVANTAGE_BASE

        if self.opponent_model is not None:
            style = self.opponent_model.get_opponent_style()
            if style == "hardliner":
                advantage += 0.25
            elif style == "late_conceder":
                advantage += 0.15
            elif style == "conceder":
                advantage -= 0.10

            recent_window = min(6, len(self.opponent_model.times))
            concession_rate = self.opponent_model.get_concession_rate(window=recent_window)
            if concession_rate is not None:
                if concession_rate >= -0.03:
                    advantage += 0.15
                elif concession_rate <= -0.18:
                    advantage -= 0.10

        if t < 0.60:
            advantage += 0.20
        elif t < 0.85:
            advantage += 0.05
        elif t < 0.95:
            advantage -= 0.05
        else:
            advantage -= 0.15

        return max(0.20, advantage)

    def _is_opponent_favorable_enough(self, offer: Outcome, our_utility: float, t: float) -> bool:
        if self.opponent_model is None:
            return True

        opponent_est = float(self.opponent_model.get_estimated_utility(offer))
        return our_utility >= opponent_est + self._required_advantage(t)

    # Here we need to return the minimum utility we can accept at given 
    # time t (in range [0,1], where 0 is the start of the negotiation and 1 is the deadline).
    # we should decrease the acc threshold closer to deadline, but it should never go below our reservation value.
    # We use AC_time + AC_asp with a Boulware like concession curve
    def acceptance_threshold(self, t: float) -> float:
        t = min(1.0, max(0.0, float(t)))
        span = max(0.0, self.max_utility - self.reservation)
        aspiration = self.reservation + span * (1 - math.pow(t, self.beta))
        return max(self.reservation, min(self.max_utility, aspiration))

    # T -> accept offer, F -> reject offer. Our mechanism to decide whether to return T Or F.
    # We always reject offers below our reservation value.
    # We use AC_next, AC_time, AC_combi to make a hybrid.
    # Saw these being used in: "Introduction to Automated Negotiation" by de Jonge.
    def should_accept(self, offer: Outcome, t: float, state: SAOState) -> bool:
        offer_utility = float(self.uFun(offer))

        if offer_utility < self.reservation:
            return False

        threshold = self.acceptance_threshold(t)
        if offer_utility >= threshold and self._is_opponent_favorable_enough(offer, offer_utility, t):
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
        previous_offers = [
            history_state.current_offer
            for history_state in self.nmi.history[:-1]
            if getattr(history_state, "current_offer", None) is not None
        ]
        if previous_offers:
            best_seen = max(float(self.uFun(previous_offer)) for previous_offer in previous_offers)
            if (
                t >= self.BEST_SEEN_LATE_STAGE
                and offer_utility >= best_seen + self.BEST_SEEN_IMPROVEMENT_MARGIN
                and offer_utility >= self.BEST_SEEN_THRESHOLD_FRACTION * threshold
                and self._is_opponent_favorable_enough(offer, offer_utility, t)
            ):
                return True

        return False
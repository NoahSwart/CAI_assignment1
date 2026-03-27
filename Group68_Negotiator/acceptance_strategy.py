import math
from negmas.common import NegotiatorMechanismInterface
from negmas.sao import SAOState
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional

from Group68_Negotiator.opponent_model import OpponentModel

class AcceptanceStrategy:
    # Concession speed in AC_time threshold. Higher => hold out longer for better offers.
    BETA = 4.0

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
        self.max_utility = self.reservation
        if best_outcome is not None:
            max_utility = float(self.uFun(best_outcome))
            if max_utility > self.max_utility: self.max_utility = max_utility

    # Computes the utility advantage required from the opponent for it to be considered favorable 
    def _required_advantage(self, t: float) -> float:
        t = min(1.0, max(0.0, float(t)))
        advantage = 0.45

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

    # Return true iff the opponent has a conceding behaviour
    # or in a general manner is willing to offer us considerable utility
    # or if we don't have information about the opponent
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
        span = self.max_utility - self.reservation
        aspiration = self.reservation + span * (1 - math.pow(t, self.BETA))
        return min(self.max_utility, aspiration)

    # T -> accept offer, F -> reject offer.
    # We always reject offers below our reservation value.
    # We use AC_next and AC_time to make a hybrid.
    # Only accept if opponent is considered favorable.
    # Use our acceptance threshold to check if an offer is acceptable.
    # When in end of negociation, apply a best seen strategy,
    # still checking if the offer is near our threshold
    def should_accept(self, offer: Outcome, t: float, state: SAOState) -> bool:
        offer_utility = float(self.uFun(offer))

        if offer_utility < self.reservation:
            return False

        threshold = self.acceptance_threshold(t)
        is_opponent_favorable = self._is_opponent_favorable_enough(offer, offer_utility, t)
        if offer_utility >= threshold and is_opponent_favorable:
            return True

        previous_offers = [
            history_state.current_offer
            for history_state in self.nmi.history[:-1]
            if getattr(history_state, "current_offer", None) is not None
        ]
        if (
            previous_offers
            and t >= 0.90
            and offer_utility >= 0.95 * threshold
            and is_opponent_favorable
        ):
            best_seen = max(float(self.uFun(previous_offer)) for previous_offer in previous_offers)
            if offer_utility >= best_seen + 0.25:
                return True

        return False
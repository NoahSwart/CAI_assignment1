from negmas import SAONegotiator, ResponseType, SAOState
from negmas.outcomes import Outcome
from typing import Optional

from Group68_Negotiator.acceptance_strategy import AcceptanceStrategy
from Group68_Negotiator.bidding_strategy import BiddingStrategy
from Group68_Negotiator.opponent_model import OpponentModel
from Group68_Negotiator.utils import get_time, is_above_reservation, outcome_utility


class Group68_Negotiator(SAONegotiator):
    # AC_next margin: accept only if current offer is meaningfully better than our next planned bid.
    NEXT_OFFER_MARGIN = 0.8
    # Deadline stage at which special late-accept logic is enabled.
    LATE_ACCEPT_TIME = 0.98
    # Minimum acceptable share of utility span near deadline (reservation + ratio * span).
    LATE_FLOOR_RATIO = 0.50

    def _adaptive_next_offer_margin(self, t: float) -> float:
        margin = self.NEXT_OFFER_MARGIN
        opponent_style = self.opponent_model.get_opponent_style()

        if opponent_style == "hardliner":
            margin += 0.40
        elif opponent_style == "late_conceder":
            margin += 0.20
        elif opponent_style == "conceder":
            margin -= 0.20

        if t < 0.60:
            margin += 0.20
        elif t < 0.85:
            margin += 0.00
        elif t < 0.95:
            margin -= 0.20
        else:
            margin -= 0.40

        return max(0.20, margin)

    def _adaptive_late_floor_ratio(self) -> float:
        ratio = self.LATE_FLOOR_RATIO
        opponent_style = self.opponent_model.get_opponent_style()

        if opponent_style == "hardliner":
            ratio += 0.10
        elif opponent_style == "late_conceder":
            ratio += 0.08
        elif opponent_style == "conceder":
            ratio -= 0.05

        return min(0.75, max(0.35, ratio))

    # Initialize all of the sub components, like bidding strategy, acceptance strategy, opponent model, etc...
    # Reset any stateful variables to prepare for a new negotiation.
    def on_negotiation_start(self, state: SAOState) -> None:
        super().on_negotiation_start(state)
        self.opponent_model = OpponentModel(self.nmi)
        self.acceptance_strategy = AcceptanceStrategy(self.nmi, self.ufun, self.opponent_model)
        self.bidding_strategy = BiddingStrategy(self.nmi, self.ufun, self.opponent_model)
        self._fallback_best_offer = self.ufun.best() if self.ufun is not None else None

    # Return the nexxt offer to send to the opponent, which we call when we need to make a bid.
    def propose(self, state: SAOState, dest: str | None = None) -> Optional[Outcome]:
        if not self.ufun:
            return None
        t = get_time(state, self.nmi)
        bid = self.bidding_strategy.get_bid(t, state)
        if bid:
            return bid

        return self._fallback_best_offer
    
    # Here we decide whether to accept offer, reject it or end the negotiation, which we call when the opponent makes an offer.
    def respond(self, state: SAOState, source: str | None = None) -> ResponseType:
        offer = state.current_offer
        if not offer or not self.ufun:
            return ResponseType.REJECT_OFFER

        t = get_time(state, self.nmi)
        self.opponent_model.update(offer, t)

        if not is_above_reservation(self.ufun, offer):
            return ResponseType.REJECT_OFFER

        if self.acceptance_strategy.should_accept(offer, t, state):
            return ResponseType.ACCEPT_OFFER

        adaptive_margin = self._adaptive_next_offer_margin(t)
        next_bid = self.propose(state)
        if (
            next_bid is not None
            and outcome_utility(self.ufun, offer)
            >= outcome_utility(self.ufun, next_bid) + adaptive_margin
        ):
            return ResponseType.ACCEPT_OFFER

        if t >= self.LATE_ACCEPT_TIME:
            late_floor_ratio = self._adaptive_late_floor_ratio()
            late_floor = float(self.ufun.reserved_value) + late_floor_ratio * (
                self.acceptance_strategy.max_utility - float(self.ufun.reserved_value)
            )
            late_minimum = max(
                float(self.ufun.reserved_value),
                self.acceptance_strategy.acceptance_threshold(t),
                late_floor,
            )
            if outcome_utility(self.ufun, offer) >= late_minimum:
                return ResponseType.ACCEPT_OFFER

        return ResponseType.REJECT_OFFER
from negmas import NegotiatorMechanismInterface
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional
from bisect import bisect_left
from random import choice


class BiddingStrategy:
    BASE_CONCESSION_EXPONENT = 4.0
    HARDLINER_CONCESSION_EXPONENT = 6.0
    LATE_CONCEDER_CONCESSION_EXPONENT = 5.4
    CONCEDER_CONCESSION_EXPONENT = 3.2
    UNKNOWN_CONCESSION_EXPONENT = 4.4

    LATE_BIDDING_TIME = 0.85
    LATE_MIN_SPAN_FRACTION = 0.45
    HARDLINER_LATE_MIN_SPAN_FRACTION = 0.55
    CONCEDER_LATE_MIN_SPAN_FRACTION = 0.40

    # These are the parameters to initialize our bidding strategy, helping the other two functions to make decisions.
    # We should pre sort by our utility (desc) to help get_bid() find a bid near our target utility efficiently.
    def __init__(
        self,
        negotiatorMechanism: NegotiatorMechanismInterface,
        utilityFunc: UtilityFunction,
        opponent_model=None,
    ):
        self.nmi = negotiatorMechanism
        self.uFun = utilityFunc
        self.opponent_model = opponent_model

        # Memory and confidence settings (easy to tune).
        self._recent_bids = []
        self._recent_memory = 3
        self._min_offers_for_opponent_model = 3

        self._reserved = float(self.uFun.reserved_value)
        self._best_bid = self.uFun.best(self.nmi.outcome_space)
        self._max_utility = float(self.uFun(self._best_bid))

        # limit the amount of outcomes we consider and sort them by utility
        sampled_outcomes = list(
            self.nmi.outcome_space.enumerate_or_sample(max_cardinality=4000)
        )
        scored = sorted(
            ((float(self.uFun(outcome)), outcome) for outcome in sampled_outcomes),
            key=lambda item: item[0],
        )

        self._utilities = [utility for utility, _ in scored]
        self._outcomes = [outcome for _, outcome in scored]

        if not self._outcomes:
            self._utilities = [self._max_utility]
            self._outcomes = [self._best_bid]

    def _register_bid(self, bid: Outcome) -> None:
        self._recent_bids.append(bid)
        if len(self._recent_bids) > self._recent_memory:
            self._recent_bids = self._recent_bids[-self._recent_memory :]

    def _filter_recent_repeats(self, candidates: list[Outcome]) -> list[Outcome]:
        non_repeated = [
            candidate
            for candidate in candidates
            if not any(candidate == previous for previous in self._recent_bids)
        ]
        return non_repeated if non_repeated else candidates

    # takes into account opponent model and does some things that i read were usefull.
    def _opponent_aware_bid(self, candidates: list[Outcome], t: float) -> Outcome:
        if not candidates:
            return self._best_bid

        if self.opponent_model is None:
            return choice(candidates)

        # Keep stronger self-focus early, shift slightly toward opponent estimate later.
        # also a good thing to tune when experimenting
        t = min(1.0, max(0.0, float(t)))
        self_w = 0.78 - 0.18 * t

        opponent_style = self.opponent_model.get_opponent_style()
        if opponent_style == "hardliner":
            self_w += 0.10
        elif opponent_style == "late_conceder":
            self_w += 0.05
        elif opponent_style == "conceder":
            self_w -= 0.06

        self_w = min(0.92, max(0.58, self_w))
        opp_w = 1.0 - self_w

        utility_span = max(1e-9, self._max_utility - self._reserved)

        #choose the bid
        best_candidate = candidates[0]
        best_score = float("-inf")
        for candidate in candidates:
            our_util = float(self.uFun(candidate))
            our_norm = (our_util - self._reserved) / utility_span
            opp_est = float(self.opponent_model.get_estimated_utility(candidate))

            score = self_w * our_norm + opp_w * opp_est
            if score > best_score:
                best_score = score
                best_candidate = candidate
        return best_candidate

    # doing the logic without enough interactions can be bad
    def _has_enough_interactions(self) -> bool:
        if self.opponent_model is None:
            return False
        if not hasattr(self.opponent_model, "total_offers"):
            return False
        return int(self.opponent_model.total_offers) >= self._min_offers_for_opponent_model

    def _adaptive_concession_exponent(self) -> float:
        exponent = self.BASE_CONCESSION_EXPONENT

        if self.opponent_model is None:
            return exponent

        style = self.opponent_model.get_opponent_style()
        if style == "hardliner":
            exponent = self.HARDLINER_CONCESSION_EXPONENT
        elif style == "late_conceder":
            exponent = self.LATE_CONCEDER_CONCESSION_EXPONENT
        elif style == "conceder":
            exponent = self.CONCEDER_CONCESSION_EXPONENT
        elif style == "unknown":
            exponent = self.UNKNOWN_CONCESSION_EXPONENT

        recent_window = min(6, len(self.opponent_model.times)) if hasattr(self.opponent_model, "times") else 0
        if recent_window >= 2:
            recent_rate = self.opponent_model.get_concession_rate(window=recent_window)
            if recent_rate is not None:
                if recent_rate >= -0.03:
                    exponent += 0.4
                elif recent_rate <= -0.18:
                    exponent -= 0.3

        return min(8.0, max(2.6, exponent))

    def _late_utility_floor(self, t: float) -> float:
        t = min(1.0, max(0.0, float(t)))
        span = max(0.0, self._max_utility - self._reserved)
        span_fraction = self.LATE_MIN_SPAN_FRACTION

        if self.opponent_model is not None:
            style = self.opponent_model.get_opponent_style()
            if style == "hardliner":
                span_fraction = self.HARDLINER_LATE_MIN_SPAN_FRACTION
            elif style == "conceder":
                span_fraction = self.CONCEDER_LATE_MIN_SPAN_FRACTION

        if t >= 0.95:
            span_fraction -= 0.08

        span_fraction = min(0.75, max(0.30, span_fraction))
        return self._reserved + span_fraction * span

    # Our strategy, returning the minimum utility we are willing to bid at time t in [0, 1].
    # At t=0 we want to be ambitous, bid high and closer to deadling we want to concede more
    # Ofcourse never under our reservation value. 

    def target_utility(self, t: float) -> float:
        t = min(1.0, max(0.0, float(t)))

        # Stadard consession
        # ONE of the values to change when experimenting is this exponent which controls how fast we concede. Higher means more stubborn.
        exponent = self._adaptive_concession_exponent()
        concession = t ** exponent
        target = self._max_utility - concession * (self._max_utility - self._reserved)
        return max(self._reserved, min(self._max_utility, target))
    
    # This is where we return the next bid we want to propse at time t.
    # Compute target utility with func above, find outcome with utility >= target and return.
    # If none exist fallback to best known outcome.
    # Another thing i saw was randomizing among near optimal outcomes makes us less predictable.
    def get_bid(self, t: float, state) -> Optional[Outcome]:
        target = self.target_utility(t)

        if t >= self.LATE_BIDDING_TIME:
            target = max(target, self._late_utility_floor(t))

        # First outcome with utility >= target.
        index = bisect_left(self._utilities, target)

        if index >= len(self._outcomes):
            return self._best_bid

        # Randomize slightly.
        neighborhood = []
        window_size = 14 if t < self.LATE_BIDDING_TIME else 24
        upper_bound = min(len(self._outcomes), index + window_size)
        for i in range(index, upper_bound):
            tolerance = 0.04 if t < self.LATE_BIDDING_TIME else 0.20
            if self._utilities[i] <= target + tolerance:
                neighborhood.append(self._outcomes[i])
            else:
                break

        candidates = neighborhood if neighborhood else [self._outcomes[index]]
        candidates = self._filter_recent_repeats(candidates)

        if self._has_enough_interactions():
            selected = self._opponent_aware_bid(candidates, t)
        else:
            selected = choice(candidates)

        self._register_bid(selected)
        return selected

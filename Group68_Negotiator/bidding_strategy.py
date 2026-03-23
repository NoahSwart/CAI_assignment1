from negmas import NegotiatorMechanismInterface
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional
from bisect import bisect_left
from random import choice


class BiddingStrategy:

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
        self_w = 0.75 - 0.20 * t
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

    # Our strategy, returning the minimum utility we are willing to bid at time t in [0, 1].
    # At t=0 we want to be ambitous, bid high and closer to deadling we want to concede more
    # Ofcourse never under our reservation value. 
    # We can use different concession curves, like Boulware (concede late), Conceder (concede early) or Linear.
    # Also more info on this in "Introduction to Automated Negotiation" by de Jonge. 
    def target_utility(self, t: float) -> float:
        t = min(1.0, max(0.0, float(t)))

        # Stadard consession
        # ONE of the values to change when experimenting is this exponent which controls how fast we concede. Higher means more stubborn.
        concession = t ** 4
        target = self._max_utility - concession * (self._max_utility - self._reserved)
        return max(self._reserved, min(self._max_utility, target))
    
    # This is where we return the next bid we want to propse at time t.
    # Compute target utility with func above, find outcome with utility >= target and return.
    # If none exist fallback to best known outcome.
    # Another thing i saw was randomizing among near optimal outcomes makes us less predictable.
    def get_bid(self, t: float, state) -> Optional[Outcome]:
        target = self.target_utility(t)

        # First outcome with utility >= target.
        index = bisect_left(self._utilities, target)

        if index >= len(self._outcomes):
            return self._best_bid

        # Randomize slightly.
        neighborhood = []
        upper_bound = min(len(self._outcomes), index + 10)
        for i in range(index, upper_bound):
            if self._utilities[i] <= target + 0.02:
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

from negmas import NegotiatorMechanismInterface
from negmas.outcomes import Outcome
from collections import defaultdict
from typing import Optional
import numpy as np


class OpponentModel:
    STYLE_MIN_OFFERS = 4
    HARDLINER_SLOPE_THRESHOLD = -0.05
    CONCEDER_SLOPE_THRESHOLD = -0.18
    LATE_CONCEDER_SLOPE_THRESHOLD = -0.08
    RECENCY_BASE = 0.5

    # These are the parameters to initialize our opponent model, helping the other two functions to make decisions.
    def __init__(self, negotiatorMechanism: NegotiatorMechanismInterface):
        self.nmi = negotiatorMechanism
        self.value_counts = defaultdict(lambda: defaultdict(int))

        self.total_offers = 0

        self.times = []
        self.estimated_utilities = []

        # Offer history so we can do recency-weighted scoring
        self.offer_history = []

        # Helper map for indexing issues
        self.issue_index = {issue: idx for idx, issue in enumerate(self.nmi.issues)}

    # Made this since the items() does not always give the same format
    def _offer_items(self, offer: Outcome):
        if hasattr(offer, "items"):
            return list(offer.items())

        if isinstance(offer, (tuple, list)):
            issue_names = []
            if hasattr(self.nmi, "outcome_space") and hasattr(self.nmi.outcome_space, "issues"):
                issue_names = [issue.name for issue in self.nmi.outcome_space.issues]

            if len(issue_names) == len(offer):
                return list(zip(issue_names, offer))

            return list(enumerate(offer))

        return []

    # Update model with opponents latest offer, which we call evertume opponent makes a bid.
    # Track frequency of values offered. Track time of offers to estimate concession rate.
    # Update frequency counts for each issue-value pair in the offer.
    def update(self, offer: Outcome, t: float) -> None:
        self.total_offers += 1
        self.offer_history.append((offer, float(t)))

        # Total of each value per issue
        for issue, value in zip(self.nmi.issues, offer):
            self.value_counts[issue][value] += 1

        est_util = self.get_estimated_utility(offer)
        self.times.append(t)
        self.estimated_utilities.append(est_util)


    # Gives more weight to recent offers
    def _recency_weight(self, t: float) -> float:
        return self.RECENCY_BASE + (1.0 - self.RECENCY_BASE) * float(t)

    # EStimate opponents utility for an outcome base on frequency of values offered.
    # More frequent values are assumed more important to the opponent, 
    # so we can assign higher utility to outcomes containing those values.
    def get_estimated_utility(self, outcome: Outcome) -> float:
        # weights estimated equally for simplicity, but might change to dynamic (as in slides)
        if self.total_offers == 0:
            return 0.0

        num_issues = len(outcome)

        if num_issues == 0 or outcome is None:
            return 0.0
        
        utility = 0.0

        # weights for each issue
        issue_weights = self.get_issue_weights()

        for issue, value in zip(self.nmi.issues, outcome):
            value_score = self._get_value_score(issue, value)
            weight = issue_weights.get(issue, 0.0)

            utility += weight * value_score

        return utility
    
    # Estimate for a specific issue-value pair. This way more recent offers will contribute more
    def _get_value_score(self, issue, value) -> float:
        if not self.offer_history:
            return 0.0

        idx = self.issue_index[issue]
        total_weight = 0.0
        value_weight = 0.0

        for offer, t in self.offer_history:
            w = self._recency_weight(t)
            total_weight += w

            if idx < len(offer) and offer[idx] == value:
                value_weight += w

        if total_weight <= 0:
            return 0.0

        return value_weight / total_weight
    
    '''
    Determines the weight of each issue based on how consistently one value appears (value frequency)
    and on how much the issue changes (stability).
    A weight would just be the value frequency multiplied by it's stability
    '''
    def get_issue_weights(self) -> dict:
        num_issues = len(self.nmi.issues)
        if num_issues == 0:
            return {}

        if self.total_offers == 0:
            return {issue: 1.0 / num_issues for issue in self.nmi.issues}

        raw_weights = {}

        for issue in self.nmi.issues:
            # for each issue we get the amount of different 
            # times a value of that issue shows up
            counts = self.value_counts[issue]

            # if there are no counts we assign the issue a standard weight
            if not counts:
                raw_weights[issue] = 1.0
                continue

            max_count = max(counts.values())
            distinct_values = len(counts)

            valueFrequency = max_count / self.total_offers
             
            if distinct_values > 0:
                stability = 1.0 / distinct_values
            else: 
                stability = 1.0

            raw_weights[issue] = valueFrequency * stability

        total_weight = sum(raw_weights.values())
        if total_weight <= 0:
            return {issue: 1.0 / num_issues for issue in self.nmi.issues}

        return {issue: w / total_weight for issue, w in raw_weights.items()}


    
    # Estimate how quickly the opponent is conceding over time.
    # Build utility over time and compute a trend (like slope of linear fit or some others they mention).
    # Positive value -> opponent is conceding, Negative value -> opponent is holding firm.
    # Return none if not enough data.
    def get_concession_rate(self, window: Optional[int] = None) -> Optional[float]:
        if len(self.times) < 2:
            return None

        if window is not None and window > 1:
            times = np.array(self.times[-window:])
            utils = np.array(self.estimated_utilities[-window:])
        else:
            times = np.array(self.times)
            utils = np.array(self.estimated_utilities)
        
        if len(times) < 2 or len(utils) < 2:
            return None
        
        if np.allclose(times, times[0]):
            return None

        # linear regression
        # getting the slope (a*t + b --> we're finding a)
        slope = np.polyfit(times, utils, 1)[0]

        return float(slope)

    def get_opponent_style(self) -> str:
        if self.total_offers < self.STYLE_MIN_OFFERS:
            return "unknown"

        overall_rate = self.get_concession_rate()
        recent_window = min(6, len(self.times))
        recent_rate = self.get_concession_rate(window=recent_window)
        current_time = float(self.times[-1]) if self.times else 0.0

        if overall_rate is None or recent_rate is None:
            return "unknown"

        if recent_rate <= self.CONCEDER_SLOPE_THRESHOLD:
            return "conceder"

        if recent_rate >= self.HARDLINER_SLOPE_THRESHOLD:
            return "hardliner"

        if current_time >= 0.60 and recent_rate <= self.LATE_CONCEDER_SLOPE_THRESHOLD:
            return "late_conceder"

        return "unknown"

    # T if opponent appears to be conceding, otherwise F. 
    # Use the function above to make decision.
    def is_opponent_conceding(self) -> bool:
        rate = self.get_concession_rate()


        if rate is None:
            return False

        # if the estimated util of opponent offers is decreasing they're conceding
        return rate < 0
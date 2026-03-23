from negmas import NegotiatorMechanismInterface
from negmas.outcomes import Outcome
from collections import defaultdict
from typing import Optional
import numpy as np


class OpponentModel:

    # These are the parameters to initialize our opponent model, helping the other two functions to make decisions.
    def __init__(self, negotiatorMechanism: NegotiatorMechanismInterface):
        self.nmi = negotiatorMechanism
        self.value_counts = defaultdict(lambda: defaultdict(int))

        self.total_offers = 0

        self.times = []
        self.estimated_utilities = []

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

        for issue, value in self._offer_items(offer):
            self.value_counts[issue][value] += 1

        est_util = self.get_estimated_utility(offer)
        self.times.append(t)
        self.estimated_utilities.append(est_util)

    # EStimate opponents utility for an outcome base on frequency of values offered.
    # More frequent values are assumed more important to the opponent, 
    # so we can assign higher utility to outcomes containing those values.
    def get_estimated_utility(self, outcome: Outcome) -> float:
        # weights estimated equally for simplicity, but might change to dynamic (as in slides)
        
        if self.total_offers == 0:
            return 0.0

        utility = 0.0
        offer_items = self._offer_items(outcome)
        num_issues = len(offer_items)

        if num_issues == 0:
            return 0.0

        for issue, value in offer_items:
            count = self.value_counts[issue][value]

            value_score = count / self.total_offers
            weight = 1.0 / num_issues

            utility += weight * value_score

        return utility
    
    # Estimate how quickly the opponent is conceding over time.
    # Build utility over time and compute a trend (like slope of linear fit or some others they mention).
    # Positive value -> opponent is conceding, Negative value -> opponent is holding firm.
    # Return none if not enough data.
    def get_concession_rate(self) -> Optional[float]:
        if len(self.times) < 2:
            return None

        # linear regression
        times = np.array(self.times)
        utils = np.array(self.estimated_utilities)

        # getting the slope (a*t + b --> we're finding a)
        slope = np.polyfit(times, utils, 1)[0]

        return slope

    # T if opponent appears to be conceding, otherwise F. 
    # Use the function above to make decision.
    def is_opponent_conceding(self) -> bool:
        rate = self.get_concession_rate()


        if rate is None:
            return False

        # if the estimated util of opponent offers is decreasing they're conceding
        return rate < 0
from negmas import NegotiatorMechanismInterface
from negmas.outcomes import Outcome
from typing import Optional


class OpponentModel:

    # These are the parameters to initialize our opponent model, helping the other two functions to make decisions.
    def __init__(self, negotiatorMechanism: NegotiatorMechanismInterface):
        self.nmi = negotiatorMechanism
        pass

    # Update model with opponents latest offer, which we call evertume opponent makes a bid.
    # Track frequency of values offered. Track time of offers to estimate concession rate.
    # Update frequency counts for each issue-value pair in the offer.
    def update(self, offer: Outcome, t: float) -> None:
        pass

    # EStimate opponents utility for an outcome base on frequency of values offered.
    # More frequent values are assumed more important to the opponent, 
    # so we can assign higher utility to outcomes containing those values.
    def get_estimated_utility(self, outcome: Outcome) -> float:
        pass
    
    # Estimate how quickly the opponent is conceding over time.
    # Build utility over time and compute a trend (like slope of linear fit or some others they mention).
    # Positive value -> opponent is conceding, Negative value -> opponent is holding firm.
    # Return none if not enough data.
    def get_concession_rate(self) -> Optional[float]:
        pass

    # T if opponent appears to be conceding, otherwise F. 
    # Use the function above to make decision.
    def is_opponent_conceding(self) -> bool:
        pass
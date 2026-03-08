from negmas import NegotiatorMechanismInterface, SAOState
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional

# Helper to get current time.
def get_time(state: SAOState, nmi: NegotiatorMechanismInterface) -> float:
    pass

# Helper to compute utility for a given outcome.
def outcome_utility(ufun: UtilityFunction, outcome: Optional[Outcome]) -> float:
    pass

# helper to check if the outcomes utility is above reservation value.
def is_above_reservation(ufun: UtilityFunction, outcome: Optional[Outcome]) -> bool:
    pass

# How far is our outcome from the Pareto frontier.
# pareto_frontier is a list of (our_util, opponent_util) tuples.
# Here we should return float('inf') if the frontier is empty.
# More info in the book: "Introduction to Automated Negotiation" by de Jonge (section Pareto efficiency)
def pareto_distance(our_util: float, opponent_util: float, pareto_frontier: list) -> float:
    pass


# How much did both parties gain above their reservation values
# Formula: max(0, our_util - our_reserved) * max(0, opponent_util - opponent_reserved)
# We return 0.0 if either party is at or below their reservation value.
#More info in the book: "Introduction to Automated Negotiation" by de Jonge (section Nash Bargaining Solution)
def nash_product(our_util: float, opponent_util: float,
                 our_reserved: float, opponent_reserved: float) -> float:
    pass
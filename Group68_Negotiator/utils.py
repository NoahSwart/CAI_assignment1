from negmas import NegotiatorMechanismInterface, SAOState
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from typing import Optional

# Helper to get current time.
def get_time(state: SAOState, nmi: NegotiatorMechanismInterface) -> float:
    if hasattr(state, "relative_time") and state.relative_time is not None:
        return float(state.relative_time);
        
    if hasattr(state, "step") and nmi.n_steps and nmi.n_steps > 0:                                                                               
      return min(1.0, max(0.0, float(state.step) / float(nmi.n_steps)))                                                                        
                                                                       
    
    return 0.0;

# Helper to compute utility for a given outcome.
def outcome_utility(ufun: UtilityFunction, outcome: Optional[Outcome]) -> float:
    if outcome is None:
        return float(ufun.reserved_value)
    return float(ufun(outcome))

# helper to check if the outcomes utility is above reservation value.
def is_above_reservation(ufun: UtilityFunction, outcome: Optional[Outcome]) -> bool:
    return outcome_utility(ufun, outcome) > float(ufun.reserved_value)

# How far is our outcome from the Pareto frontier.
# pareto_frontier is a list of (our_util, opponent_util) tuples.
# Here we should return float('inf') if the frontier is empty.
# More info in the book: "Introduction to Automated Negotiation" by de Jonge (section Pareto efficiency)
def pareto_distance(our_util: float, opponent_util: float, pareto_frontier: list) -> float:
    if pareto_frontier:
        min_distance = float("inf")
        for ourF, oppF in pareto_frontier:
            distance = ((ourF - our_util) ** 2 + (oppF - opponent_util) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
        return min_distance
    else:
        return float("inf")


# How much did both parties gain above their reservation values
# Formula: max(0, our_util - our_reserved) * max(0, opponent_util - opponent_reserved)
# We return 0.0 if either party is at or below their reservation value.
#More info in the book: "Introduction to Automated Negotiation" by de Jonge (section Nash Bargaining Solution)
def nash_product(our_util: float, opponent_util: float,
                 our_reserved: float, opponent_reserved: float) -> float:
    our_gain = max(0.0, our_util - our_reserved)
    opponent_gain = max(0.0, opponent_util - opponent_reserved)

    if our_gain == 0.0 or opponent_gain == 0.0:
        return 0.0

    return our_gain * opponent_gain
import random
from negmas.sao import SAONegotiator, ResponseType
import itertools
import math
from negmas.preferences import TriangularFun, TableFun
from negmas.outcomes import Issue

"""
Implementation of the ChargingBoul negotiation agent
This agent is both adaptive and time-based.
This agent only really makes sense if there are more than 2^5 rounds due to the UBI calculations...
Implementation is based on this paper: https://arxiv.org/html/2512.06595v1
"""

# Parameters to tweak for this class
P_MIN: float = 0.5 # Minimum utility that the agent is willing to propose
P_MAX: float = 1.0 # Utility goal to start with
P_LATE: float = 0.55 # Minimum utility in the final moments of the negotiation

P_LATE_MAP = {
    "Conceder": 0.25, # Boulware and Conceder at the end are quite similar, although conceder has a less-steep curve.
    "Boulware": 0.6, # Value from our tests
    "Hardliner": 0.65 # We don't concede more for hardliners >:(
}

# Concession exponent settings
# Smaller e => slower concessions
# Larger e => faster concessions
# The exponent will be picked based on the classification of our opponent
# Boulware, Hardliner or Conceder
# Hence, different e-values need to be set.
# As an indication, you can interpret 0.1 as 'very stubborn' and 0.5 as 'more willing to move'
# Please DO NOT alter the names in the E_MAP variable as this will make it default to the value for "unknown".
E_UNKNOWN: float = 0.2

E_MAP = {
    "Boulware": 0.3,
    "Hardliner": 0.2,
    "Conceder": 0.2
}

# Tolerance Variable (epsilon).
# Domain with fewer bids -> Larger epsilon (0.05)
# Domain with more bids -> Smaller epsilon (0.001) to make less big concessions early
EPSILON: float = 0.05

# For the novel acceptance strategy, we predict using the proposal method from the BayesianNegotiator.
# This value is usually too high, so we need a margin below that proposal in which we are willing to still accept.
# Based on the opponent class, we choose one of the values below.
# For example: When the opponent is hard-headed, we are not willing to make big compromises, because our opponent isn't either.
B_MAP = {
    "Unknown": 0.06,
    "Boulware": 0.06,
    "Hardliner": 0.07,
    "Conceder": 0.05
}

# If the outcome space is continuous, we need to sample the outcome space to save on resources
# This variable controls how many outcomes should be sampled
SAMPLE_OUTCOME_SPACE_AMOUNT: int = 1000

# Experimental:
# greedy (1) -> only propose offers above or equal to your utility goal and never below
# greedy (2) -> propose the best offer above your utility goal :D
GREEDY: int = 0

# Boolean that decides whether to use the novel acceptance strategy instead of ACnext
USE_NOVEL_ACCEPTANCE: bool = True

class ChargingBayes(SAONegotiator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_possible_outcomes = []

        # Array to keep the opponents offers in.
        # Used in several components of this agent.
        self.opponent_history = []

        # Array to keep a history of utilities from the opponents offer.
        # Used in several components of this agent, notably in the AUI calculation.
        self.opponent_utilities = []

        # Variable to store the best offer so far in, so we don't have to re-calculate it several times.
        self.best_opponent_offer = None

        # We will try estimating the opponent class in one of three categories:
        # Boulware, Hardliner, Conceder
        # If UBI >= 5 -> Boulware
        # If UBI < 5 and AUI <= 2 -> Hardliner
        # If UBI < 5 and AUI > 2 -> Conceder
        self.opponent_class = "Unknown"

        # Hyperparameters for ChargingBoul
        self.p_min = P_MIN # Minimum utility that the agent is willing to accept
        self.p_max = P_MAX # Utility goal to start with
        self.e_unknown = E_UNKNOWN # Concession exponent for opponent class "Unknown"
        self.e_map = E_MAP # Map of (K, V) pairs in format (opponent_class, e_value for that opponent class)
        self.epsilon = EPSILON # Tolerance value to control granularity of offer range (see paper)

        self.weight_hypotheses = []
        self.priors = []
        self.sigma = 1
        self.current_state = None

        self.late_init = False

    def on_preferences_changed(self, changes):
        super().on_preferences_changed(changes)

        issues = self.nmi.issues
        num_issues = len(issues)

        possible_weights = self.get_weights()
        possible_utility_functions = [self.get_utility_functions(issues[x]) for x in range(num_issues)]
        all_function_combos = list(itertools.product(*possible_utility_functions))

        self.weight_hypotheses = list(itertools.product(possible_weights, all_function_combos))
        self.priors = [1 / len(self.weight_hypotheses)] * len(self.weight_hypotheses)

    def on_negotiation_start(self, state):
        # Cache "All" outcomes, to save some time during the proposal phase
        # Either the outcome space is discrete or continuous.
        # If it is continuous, sample the outcome space because else you will have a big calculation
        if self.nmi.outcome_space.is_discrete():
            outcomes = list(self.nmi.outcome_space.enumerate_or_sample())
        else:
            outcomes = list(self.nmi.outcome_space.sample(SAMPLE_OUTCOME_SPACE_AMOUNT))

        self.all_possible_outcomes = [(self.ufun(o), o) for o in outcomes]
        self.late_init = False


    def on_opponent_action(self, state, incoming_offer):
        """Update the Opponent Model based on new incoming bids"""
        if incoming_offer:
            # Append the incoming offer to the history of offers made
            self.opponent_history.append(incoming_offer)
            # Calculate the utility that that offer has for us
            incoming_offer_utility = self.ufun(incoming_offer)
            # And append that to the history of utilities
            self.opponent_utilities.append(incoming_offer_utility)

            # Under here, we set the amount of times we have to update our opponent classification
            # You can change this, but it only makes sense to do this after at least 3 offers are made.
            # Hint: You can also change this to a modulo, so e.g. len(self.opponent_history) % 10 == 0 for every 10 steps
            if len(self.opponent_history) > 2:
                self.update_opponent_classification()

    def respond(self, state, source: str | None = None):
        """
        Respond:
        If USE_NOVEL_ACCEPTANCE:
        ...
        else:
            ACnext
        """
        if not state.current_offer:
            return ResponseType.REJECT_OFFER

        self.on_opponent_action(state, state.current_offer)

        # Cache the best offer made by the opponent so far, so we can re-purpose it later in the "late round" logic
        if not self.best_opponent_offer or self.ufun(self.best_opponent_offer) < self.ufun(state.current_offer):
            self.best_opponent_offer = state.current_offer

        self.current_state = state
        self.update_all_p_h_j_given_bid_t(state.current_offer)

        if USE_NOVEL_ACCEPTANCE and len(self.opponent_history) > 20:
            bayes_offer = self.propose_bayes(state)
            bayes_offer_utility = self.ufun(bayes_offer)

            # See B_MAP documentation above. We select a value from the B_MAP based on our opponent class.
            # We then take bayes_offer utility - <the value from B_MAP>.
            # After that, it's similar to ACnext, in the sense that we check if the opponents offers utility is above this, we accept, else reject.
            if (bayes_offer_utility - B_MAP.get(self.opponent_class, B_MAP.get("Unknown", 0.025))) <= self.ufun(state.current_offer):
                return ResponseType.ACCEPT_OFFER
            return ResponseType.REJECT_OFFER

        else:
            offer = self.propose(state)
            my_utility = self.ufun(offer)
            # ACnext
            if my_utility <= self.ufun(state.current_offer):
                return ResponseType.ACCEPT_OFFER
            return ResponseType.REJECT_OFFER

    def propose_bayes(self, state):
        all_outcomes = self.all_possible_outcomes
        aspiration = 1 - (state.relative_time ** 4) * (1 - self.ufun.reserved_value)
        acceptable = [out[1] for out in all_outcomes if out[0] >= aspiration]

        if not acceptable:
            return None

        highest_prob_idx = self.priors.index(max(self.priors))
        weights, functions = self.weight_hypotheses[highest_prob_idx]

        return max(
            acceptable,
            key=lambda offer: self.ufun(offer) +
                              sum(w * func(v) for w, v, func in zip(weights, offer, functions))
        )

    def propose(self, state, dest: str | None = None):
        """Step 3: Bidding Strategy (Boulware-like with adaptations)."""
        t = state.relative_time

        # If we're nearing the negotiation time limit, we make more drastic concessions
        # To decide whether we're in the final moments of the negotiation, we use the formula from the paper
        # Here, we call the "final moments" of the negotiations "is_late" (True or False)
        # The formula to determine whether we're in the final moments: t > 1 - 0.5^ubi
        # However before any ubi calculations, ubi may be 0, hence guard against the case where ubi = 0.
        ubi = self.calculate_ubi(self.opponent_history, 0)
        is_late = ubi > 0 and t > 1.0 - (0.5 ** ubi)

        if is_late:
            # Lower your minimum acceptable value at the end of the round
            self.p_min = P_LATE_MAP.get(self.opponent_class, P_LATE)
            # If the best received utility so far is greater than p_min
            if self.ufun(self.best_opponent_offer) > self.p_min:
                # and the predicted opponent utility (using propose_bayes) is less than 2 * p_min then ChardingBoul re-proposes the bid.
                if self.ufun(self.propose_bayes(state)) - B_MAP.get(self.opponent_class, B_MAP.get("Unknown", 0.025)) < 2 * self.p_min:
                    return self.best_opponent_offer

        # Adjust target utility based on opponent class
        g_t = self.calculate_utility_goal(t)

        # Calculate the outcome utility range
        outcome_utility_range = ChargingBayes.calculate_offer_range(g_t, t, self.epsilon)

        # Greedy (1) strategy: only propose offers above or equal to your current utility goal
        if GREEDY == 1:
            outcome_utility_range = tuple[g_t, outcome_utility_range[1]]

        # Filter the outcomes that fall into our outcome_utility_range
        outcomes_in_range = [o for o in self.all_possible_outcomes if outcome_utility_range[0] <= o[0] <= outcome_utility_range[1]]

        # Greedy (2) strategy: always propose the best offer in your utility range
        if GREEDY == 2:
             return max(outcomes_in_range, key=lambda x: x[0])[1]

        # Default strategy: propose a random offer that falls inside the outcome range
        if outcomes_in_range:
            return random.choice(outcomes_in_range)[1]

        # If the outcomes_in_range is empty, then we still need to propose something...
        # So then we select the best outcome closest to the utility goal
        candidate_outcomes = [o for o in self.all_possible_outcomes if o[0] >= self.p_min]
        return min(self.all_possible_outcomes, key=lambda o: abs(float(o[0]) - g_t))[1]

    def calculate_utility_goal(self, time):
        """
        Function to calculate the utility goal from the paper
        g(t) = m + (1-m)(1-t^{1/e})
        """
        e = self.e_map.get(self.opponent_class, self.e_unknown)

        # Calculate utility goal
        utility_goal = self.p_min + (self.p_max - self.p_min) * (1 - (time ** (1 / e)))

        return utility_goal

    @staticmethod
    def calculate_offer_range(g_t, time, epsilon) -> tuple[float, float]:
        """
        Calculates the range of utilities from which a proposal will be chosen
        [g(t) - (3t+1)*epsilon, g(t) + (3t+1)*epsilon]
        :param g_t: The value of calculate_utility_goal
        :param time: The current time
        :param epsilon: Tolerance value, typically 0.001 to 0.05
        :return: The offer utility range
        """
        return g_t - (3 * time + 1) * epsilon, g_t + (3 * time + 1) * epsilon

    def update_opponent_classification(self):
        """Classify the opponent based on the UBI and ABI statistics"""
        ubi = self.calculate_ubi(self.opponent_history, 0)
        aui = self.calculate_aui(self.opponent_utilities, 0)

        # As mentioned in the paper:
        # If UBI >= 5 -> Boulware
        # If UBI < 5 and AUI <= 2 -> Hardliner
        # If UBI < 5 and AUI > 2 -> Conceder
        if ubi >= 5:
            self.opponent_class = "Boulware"
        elif aui <= 2:
            self.opponent_class = "Hardliner"
        else:
            self.opponent_class = "Conceder"

        # Adapt concession severity if opponent is Boulware
        self.e_map["Boulware"] = 0.2 * (2 ** (5 - ubi))

    def calculate_ubi(self, received_bids, ubi):
        """
        Function that calculates the Unique Bid Index (UBI)
        Initial call must be with ubi = 0
        :param received_bids: The received offers so far
        :param ubi: The ubi value initially, used in recursion
        :return: The Ubique Bid Index
        """
        left_half = received_bids[:len(received_bids) // 2]
        right_half = received_bids[len(received_bids) // 2:]
        len_left = len(left_half)
        len_right = len(right_half)
        # This if is the same as: len_left > 0 && len_right > 0 && len_left < len_right
        if 0 < len_left < len_right and len_right > 0:
            return self.calculate_ubi(right_half, ubi + 1)
        return ubi

    def calculate_aui(self, received_utils, aui):
        """
        Function that calcluates the Average Utility Index (AUI)
        Initial call must be with aui = 0
        :param received_utils: The utility of the received offers so far
        :param aui: The AUI value initially, used in recursion
        :return: The Average Utility Index
        """
        left_half = received_utils[:len(received_utils) // 2]
        right_half = received_utils[len(received_utils) // 2:]
        len_left = len(left_half)
        len_right = len(right_half)
        if len_left == 0 or len_right == 0:
            return aui
        mean_left = sum(left_half) / len(left_half)
        mean_right = sum(right_half) / len(right_half)
        if len_left > 0 and len_right > 0 and mean_left < mean_right:
            return self.calculate_aui(left_half, aui + 1)
        return aui


    def get_weights(self):
        n = len(self.nmi.issues)

        resolution = 10
        weights = []

        for comb in itertools.product(range(resolution + 1), repeat=n):
            if sum(comb) == resolution:
                weights.append([c / resolution for c in comb])

        return weights


    def get_utility_functions(self, issue: Issue):
        epsilon = 0.01

        if issue.is_discrete() and not issue.is_integer():
            values = issue.values

            mapping_equal = {
                val: 1 / len(values)
                for val in issue.values
            }

            utility_functions = [TableFun(mapping_equal)]

            for val_pref in issue.values:
                mapping_1_preferred = {
                    val: (1 / 2 if val == val_pref else 1 / (len(issue.values) * 2))
                    for val in issue.values
                }
                utility_functions.append(TableFun(mapping_1_preferred))

            return utility_functions

        if issue.is_continuous() or issue.is_integer():
            low, high = float(issue.min_value), float(issue.max_value)
            middle = (high-low) / 2
            return [
                TriangularFun(low - epsilon, low, high + epsilon),
                TriangularFun(low - epsilon, high, high + epsilon),
                TriangularFun(low, middle, high)
            ]

        raise Exception ("Not a correct issue")

    def utility_dash(self):
        if self.opponent_class == "Boulware":
            return 1.0 - (self.current_state.relative_time ** 4) * 0.3

        elif self.opponent_class == "Conceder":
            return 1.0 - (self.current_state.relative_time ** 0.5) * 0.3

        elif self.opponent_class == "Hardliner":
            return 1

        elif self.opponent_class == "Unknown":
            return 1.0 - self.current_state.relative_time * 0.3

        else:
            raise Exception("Not a correct opponent")

    def u_bid_t_given_h_j(self, bid_t, h_j):
        weights, functions = h_j
        utility = sum(w * f(v) for w, f, v in zip(weights, functions, bid_t))
        return utility

    def update_sigma(self):
        self.sigma = max(0.3, self.sigma * 0.95)

    def p_bid_t_given_h_j(self, bid_t, h_j):
        self.update_sigma()
        exponent = - pow(self.u_bid_t_given_h_j(bid_t, h_j) - self.utility_dash(), 2) / (2 * pow(self.sigma, 2))
        return pow(math.e, exponent) / (self.sigma * math.sqrt(2 * math.pi))

    def update_all_p_h_j_given_bid_t(self, bid_t):
        all_p_h_j_given_bid_t = []
        priors = self.priors

        for h_j_idx in range (len(self.weight_hypotheses)):
            h_j = self.weight_hypotheses[h_j_idx]
            prior = priors[h_j_idx]

            all_p_h_j_given_bid_t.append(prior * self.p_bid_t_given_h_j(bid_t, h_j))

        sum_of_odds = sum(all_p_h_j_given_bid_t)
        new_priors = [x / sum_of_odds for x in all_p_h_j_given_bid_t]

        self.priors = new_priors


def set_parameters(p_min, p_max, p_late, p_late_conceder, p_late_boul, p_late_hardliner,
                   e_unknown, e_conceder, e_boul, e_hardliner, epsilon,
                   b_unknown, b_conceder, b_boul, b_hardliner,
                   ) -> None:
    """
    Method to set the hyperparameters of ChargingBayes (used mainly in hyperparam_tester)
    """
    global P_MIN, P_MAX, P_LATE, P_LATE_MAP, E_UNKNOWN, E_MAP, EPSILON, B_MAP
    P_MIN = p_min
    P_MAX = p_max
    P_LATE = p_late
    P_LATE_MAP = {
        "Conceder": p_late_conceder,
        "Boulware": p_late_boul,
        "Hardliner": p_late_hardliner,
    }
    E_UNKNOWN = e_unknown
    E_MAP = {
        "Conceder": e_conceder,
        "Boulware": e_boul,
        "Hardliner": e_hardliner,
    }
    EPSILON = epsilon
    B_MAP = {
        "Unknown": b_unknown,
        "Boulware": b_boul,
        "Hardliner": b_hardliner,
        "Conceder": b_conceder
    }

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent)) # check one level up for imports
from Group68_Negotiator.group_68_negotiator import GroupN_Negotiator

# Run our agent against itself for a basic sanity check.
# Set up negMAS negotiation session with the two agent instances.
# repeat n_repetitions times across at least one domain.
# Print utility of each side and whether agreement was reached.
def run_self_play(n_repetitions: int = 5):
    pass

# Run our agent against all other agents, repeat n times per matchup and collect results.
# Test on multiple domains to check how well our agent generalizes.
# Return a data frame that looks something like this (can be changed): ["agent", "opponent", "our_utility", "opp_utility", "agreement", "nash_product"]
# More info on "Introduction to Automated Negotiation" by de Jonge (section tournamnets).
def run_tournament(agents: list, n_repetitions: int = 10) -> pd.DataFrame:
    pass

# Summarize the tournament results.
# We Must include: average utility, agreement rate, average Nash product,
# average social welfare and average Pareto distance.
def compute_metrics(results: pd.DataFrame) -> dict:
    pass

# Generate and save plots for the report. All types of graphs would be nice.
def plot_results(results: pd.DataFrame, save_path: str = "results.png") -> None:
    pass


if __name__ == "__main__":
    run_self_play(n_repetitions=3)

    opponents = []
    results = run_tournament([GroupN_Negotiator] + opponents, n_repetitions=5)
    metrics = compute_metrics(results)
    print("Metrics:", metrics)
    plot_results(results, save_path="results.png")
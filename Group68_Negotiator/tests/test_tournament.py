import pandas as pd
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Allow running this file both directly and as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from negmas import make_issue, SAOMechanism
from negmas.preferences import LinearAdditiveUtilityFunction as UFun                                                                         
from negmas.preferences.value_fun import AffineFun                                                                                           
from Group68_Negotiator.utils import outcome_utility, nash_product 
from Group68_Negotiator.group_68_negotiator import Group68_Negotiator

#Helper to create utility functions
def create_uFun(issues):
    buyer_ufun = UFun(values=[AffineFun(-1, 9)], weights=[1.0], issues=issues, reserved_value=0.0)
    seller_ufun = UFun(values=[AffineFun(1, 0)], weights=[1.0], issues=issues, reserved_value=0.0)
    return buyer_ufun, seller_ufun

def extract_agreement(result):
    if result is None or result.agreement is None:
        return None
    return result.agreement

# Run our agent against itself for a basic sanity check.
# Set up negMAS negotiation session with the two agent instances.
# repeat n_repetitions times across at least one domain.
# Print utility of each side and whether agreement was reached.
def run_self_play(n_repetitions: int = 5):
    issues = [make_issue(name="price", values=10)]

    for i in range(n_repetitions):
        mechanism = SAOMechanism(issues=issues, n_steps=20)

        buyer_ufun, seller_ufun = create_uFun(issues)

        buyer = Group68_Negotiator(name=f"selfbuyer_{i+1}", ufun=buyer_ufun)
        seller = Group68_Negotiator(name=f"selfseller_{i+1}", ufun=seller_ufun)

        mechanism.add(buyer)
        mechanism.add(seller)

        result = mechanism.run()
        agreement = extract_agreement(result)

        buyer_utility = outcome_utility(buyer.ufun, agreement)
        seller_utility = outcome_utility(seller.ufun, agreement)

        print(f"Self-play {i+1}: Agreement: {agreement}, Buyer Utility: {buyer_utility}, Seller Utility: {seller_utility}, Agreement Reached: {agreement is not None}")

# Run our agent against all other agents, repeat n times per matchup and collect results.
# Test on multiple domains to check how well our agent generalizes.
# Return a data frame that looks something like this (can be changed): ["agent", "opponent", "our_utility", "opp_utility", "agreement", "nash_product"]
# More info on "Introduction to Automated Negotiation" by de Jonge (section tournamnets).
def run_tournament(agents: list, n_repetitions: int = 10) -> pd.DataFrame:
    columns = ["agent", "opponent", "repetition", "our_utility", "opp_utility", "agreement", "nash_product", "final_offer"]
    results = []

    issues = [make_issue(name="price", values=10)]
    for opponent_class in agents:
        if opponent_class == Group68_Negotiator:
            continue  # Skip self-play

        for i in range(n_repetitions):
            mechanism = SAOMechanism(issues=issues, n_steps=20)

            our_ufun, opp_ufun = create_uFun(issues)
            our_agent = Group68_Negotiator(name=f"agent_Group68_{i+1}", ufun=our_ufun)
            opp_agent = opponent_class(name=f"{opponent_class.__name__}_{i+1}", ufun=opp_ufun)  

            mechanism.add(our_agent)
            mechanism.add(opp_agent)

            result = mechanism.run()
            agreement = extract_agreement(result)
            our_utility = outcome_utility(our_agent.ufun, agreement)
            opp_utility = outcome_utility(opp_agent.ufun, agreement)

            results.append({
                "agent": Group68_Negotiator.__name__,                                                                                                
                "opponent": opponent_class.__name__,
                "repetition": i + 1,
                "our_utility": our_utility,
                "opp_utility": opp_utility,
                "agreement": agreement is not None,
                "nash_product": nash_product(our_utility, opp_utility, our_agent.ufun.reserved_value, opp_agent.ufun.reserved_value),
                "final_offer": agreement
            })
    return pd.DataFrame(results, columns=columns)

# Summarize the tournament results.
# We Must include: average utility, agreement rate, average Nash product,
# average social welfare and average Pareto distance.
def compute_metrics(results: pd.DataFrame) -> dict:
    if results.empty:                                                                                                                        
        return {                                                                                                                             
            "avg_utility": 0.0,                                                                                                              
            "agreement_rate": 0.0,                                                                                                           
            "avg_nash_product": 0.0,                                                                                                         
            "avg_social_welfare": 0.0,                                                                                                       
            "avg_pareto_distance": None,                                                                                                     
        }
    metrics = {
        "avg_utility": float(results["our_utility"].mean()),
        "agreement_rate": float(results["agreement"].mean()),
        "avg_nash_product": float(results["nash_product"].mean()),
        "avg_social_welfare": float(
            (results["our_utility"] + results["opp_utility"]).mean()
        ),
    }

    if "pareto_distance" in results.columns:
        metrics["avg_pareto_distance"] = float(results["pareto_distance"].mean())
    else:
        metrics["avg_pareto_distance"] = None

    return metrics                                                                                                                                     
                                                                                                                                      

# Generate and save plots for the report. All types of graphs would be nice.
def plot_results(results: pd.DataFrame, save_path: str = "results.png"):
    if results.empty:
        print("No results to plot.")
        return

    # Extra metric
    results["social_welfare"] = results["our_utility"] + results["opp_utility"]
    # Average results per opponent
    summary = results.groupby("opponent").mean()
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # Agreement rate
    summary["agreement"].plot(kind="bar", ax=axes[0,0], title="Agreement Rate")
    # Utilities
    summary[["our_utility", "opp_utility"]].plot(
        kind="bar",
        ax=axes[0,1],
        title="Average Utility"
    )
    # Nash product
    summary["nash_product"].plot(kind="bar", ax=axes[1,0], title="Nash Product")
    # Social welfare
    summary["social_welfare"].plot(kind="bar", ax=axes[1,1], title="Social Welfare")

    for ax in axes.flatten():
        ax.set_xlabel("Opponent")
        ax.tick_params(axis="x", rotation=20)

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

if __name__ == "__main__":
    run_self_play(n_repetitions=3)

    opponents = []
    results = run_tournament([Group68_Negotiator] + opponents, n_repetitions=5)
    metrics = compute_metrics(results)
    print("Metrics:", metrics)
    plot_results(results, save_path="results.png")

import pandas as pd
import sys
import json
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Optional

# Allow running this file both directly and as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from negmas import make_issue, SAOMechanism
from negmas.sao import (
    AspirationNegotiator,
    BoulwareTBNegotiator,
    ConcederTBNegotiator,
    RandomNegotiator,
    ToughNegotiator,
)
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


def _proposer_role(proposer_id: Optional[str], our_agent_name: str, opp_agent_name: str) -> str:
    if proposer_id is None:
        return "unknown"

    proposer = str(proposer_id)
    if proposer.startswith(f"{our_agent_name}-"):
        return "our_agent"
    if proposer.startswith(f"{opp_agent_name}-"):
        return "opponent"
    return "unknown"


def _build_trace_rows(
    mechanism: SAOMechanism,
    our_agent_name: str,
    opp_agent_name: str,
    our_ufun,
    opp_ufun,
    match_id: str,
    opponent_name: str,
    repetition: int,
    role: str,
    start_order: str,
    agreement,
):
    rows = []
    history = mechanism.history

    for index, state in enumerate(history):
        offer = state.current_offer
        proposer_id = getattr(state, "current_proposer", None)
        proposer_role = _proposer_role(proposer_id, our_agent_name, opp_agent_name)

        rows.append({
            "match_id": match_id,
            "agent": Group68_Negotiator.__name__,
            "opponent": opponent_name,
            "repetition": repetition,
            "role": role,
            "start_order": start_order,
            "history_index": index,
            "step": int(getattr(state, "step", index)),
            "relative_time": float(getattr(state, "relative_time", 0.0)),
            "offer_price": offer[0] if offer is not None and len(offer) > 0 else None,
            "proposer_role": proposer_role,
            "our_utility_on_offer": float(our_ufun(offer)) if offer is not None else None,
            "opp_utility_on_offer": float(opp_ufun(offer)) if offer is not None else None,
            "is_agreement_offer": bool(agreement is not None and offer == agreement),
        })

    return rows

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
def run_tournament(agents: list, n_repetitions: int = 10, return_trace: bool = False):
    columns = [
        "agent",
        "opponent",
        "repetition",
        "role",
        "start_order",
        "our_utility",
        "opp_utility",
        "agreement",
        "nash_product",
        "final_offer",
        "n_rounds",
        "match_id",
        "offer_sequence",
    ]
    results = []
    trace_rows = []

    issues = [make_issue(name="price", values=10)]
    for opponent_class in agents:
        if opponent_class == Group68_Negotiator:
            continue  # Skip self-play

        for i in range(n_repetitions):
            buyer_ufun, seller_ufun = create_uFun(issues)
            role_configs = [
                ("our_buyer", buyer_ufun, seller_ufun),
                ("our_seller", seller_ufun, buyer_ufun),
            ]
            start_order_configs = ["our_first", "our_second"]

            for role_label, our_ufun, opp_ufun in role_configs:
                for start_order in start_order_configs:
                    mechanism = SAOMechanism(issues=issues, n_steps=20)

                    our_agent = Group68_Negotiator(
                        name=f"agent_Group68_{role_label}_{start_order}_{i+1}",
                        ufun=our_ufun,
                    )
                    opp_agent = opponent_class(
                        name=f"{opponent_class.__name__}_{role_label}_{start_order}_{i+1}",
                        ufun=opp_ufun,
                    )

                    if start_order == "our_first":
                        mechanism.add(our_agent)
                        mechanism.add(opp_agent)
                    else:
                        mechanism.add(opp_agent)
                        mechanism.add(our_agent)

                    result = mechanism.run()
                    agreement = extract_agreement(result)
                    our_utility = outcome_utility(our_agent.ufun, agreement)
                    opp_utility = outcome_utility(opp_agent.ufun, agreement)
                    history = mechanism.history
                    match_id = f"{opponent_class.__name__}_{role_label}_{start_order}_rep_{i+1}"

                    offer_sequence = [state.current_offer for state in history]

                    trace_rows.extend(
                        _build_trace_rows(
                            mechanism=mechanism,
                            our_agent_name=our_agent.name,
                            opp_agent_name=opp_agent.name,
                            our_ufun=our_agent.ufun,
                            opp_ufun=opp_agent.ufun,
                            match_id=match_id,
                            opponent_name=opponent_class.__name__,
                            repetition=i + 1,
                            role=role_label,
                            start_order=start_order,
                            agreement=agreement,
                        )
                    )

                    results.append({
                        "agent": Group68_Negotiator.__name__,
                        "opponent": opponent_class.__name__,
                        "repetition": i + 1,
                        "role": role_label,
                        "start_order": start_order,
                        "our_utility": our_utility,
                        "opp_utility": opp_utility,
                        "agreement": agreement is not None,
                        "nash_product": nash_product(our_utility, opp_utility, our_agent.ufun.reserved_value, opp_agent.ufun.reserved_value),
                        "final_offer": agreement,
                        "n_rounds": len(history),
                        "match_id": match_id,
                        "offer_sequence": json.dumps(offer_sequence),
                    })

    summary_df = pd.DataFrame(results, columns=columns)
    if not return_trace:
        return summary_df

    trace_df = pd.DataFrame(trace_rows)
    return summary_df, trace_df

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
    summary = results.groupby("opponent").mean(numeric_only=True)
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


def save_readable_traces(trace: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for opponent_name, opponent_trace in trace.groupby("opponent"):
        sorted_trace = opponent_trace.sort_values(["repetition", "step", "history_index"])
        lines = []

        for match_id, match_trace in sorted_trace.groupby("match_id", sort=False):
            role_label = str(match_trace.iloc[0]["role"]) if "role" in match_trace.columns else "unknown"
            start_order = str(match_trace.iloc[0]["start_order"]) if "start_order" in match_trace.columns else "unknown"
            lines.append(f"{match_id} ({role_label}, {start_order}):")
            for _, row in match_trace.iterrows():
                agreement_mark = " | AGREEMENT" if bool(row["is_agreement_offer"]) else ""
                lines.append(
                    "  "
                    f"t={float(row['relative_time']):.3f}"
                    f" | step={int(row['step'])}"
                    f" | price={int(row['offer_price'])}"
                    f" | proposer={row['proposer_role']}"
                    f" | our_u={float(row['our_utility_on_offer']):.2f}"
                    f" | opp_u={float(row['opp_utility_on_offer']):.2f}"
                    f"{agreement_mark}"
                )
            lines.append("")
            lines.append("")

        output_path = output_dir / f"{opponent_name}.txt"
        output_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    run_self_play(n_repetitions=3)

    opponents = [
        AspirationNegotiator,
        BoulwareTBNegotiator,
        ConcederTBNegotiator,
        RandomNegotiator,
        ToughNegotiator,
    ]
    results, trace = run_tournament([Group68_Negotiator] + opponents, n_repetitions=10, return_trace=True)
    metrics = compute_metrics(results)
    print("Metrics:", metrics)
    results_path = "tournament_results.csv"
    results.to_csv(results_path, index=False)
    print(f"Saved detailed results to {results_path}")

    readable_trace_dir = Path("tournament_traces")
    save_readable_traces(trace, readable_trace_dir)
    print(f"Saved readable traces to {readable_trace_dir}")

    plot_results(results, save_path="results.png")
    print("Saved plot to results.png")

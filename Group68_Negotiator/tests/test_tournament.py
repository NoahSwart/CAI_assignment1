import json
import sys
from pathlib import Path
from typing import Callable, Optional

import matplotlib.pyplot as plt
import pandas as pd

# Allow running this file both directly and as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from negmas import SAOMechanism, make_issue
from negmas.preferences import LinearAdditiveUtilityFunction as UFun
from negmas.preferences.value_fun import AffineFun
from negmas.sao import (
    AspirationNegotiator,
    BoulwareTBNegotiator,
    ConcederTBNegotiator,
    RandomNegotiator,
    ToughNegotiator,
)

from Group68_Negotiator.group_68_negotiator import Group68_Negotiator
from Group68_Negotiator.utils import nash_product, outcome_utility


DomainBuilder = Callable[[], tuple[list, UFun, UFun, int]]


def build_single_issue_10() -> tuple[list, UFun, UFun, int]:
    issues = [make_issue(name="price", values=10)]
    buyer_ufun = UFun(
        values=[AffineFun(-1, 9)],
        weights=[1.0],
        issues=issues,
        reserved_value=0.0,
    )
    seller_ufun = UFun(
        values=[AffineFun(1, 0)],
        weights=[1.0],
        issues=issues,
        reserved_value=0.0,
    )
    return issues, buyer_ufun, seller_ufun, 20


def build_single_issue_50_overlap() -> tuple[list, UFun, UFun, int]:
    issues = [make_issue(name="price", values=50)]
    buyer_ufun = UFun(
        values=[AffineFun(-1, 49)],
        weights=[1.0],
        issues=issues,
        reserved_value=34.0,
    )
    seller_ufun = UFun(
        values=[AffineFun(1, 0)],
        weights=[1.0],
        issues=issues,
        reserved_value=12.0,
    )
    return issues, buyer_ufun, seller_ufun, 30


def build_two_issue_5x5() -> tuple[list, UFun, UFun, int]:
    issues = [
        make_issue(name="price", values=5),
        make_issue(name="delivery_time", values=5),
    ]
    buyer_ufun = UFun(
        values=[AffineFun(-1, 4), AffineFun(-1, 4)],
        weights=[0.6, 0.4],
        issues=issues,
        reserved_value=1.2,
    )
    seller_ufun = UFun(
        values=[AffineFun(1, 0), AffineFun(1, 0)],
        weights=[0.6, 0.4],
        issues=issues,
        reserved_value=1.2,
    )
    return issues, buyer_ufun, seller_ufun, 25


def benchmark_domains() -> dict[str, DomainBuilder]:
    return {
        "single_issue_10": build_single_issue_10,
        "single_issue_50_overlap": build_single_issue_50_overlap,
        "two_issue_5x5": build_two_issue_5x5,
    }


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
    domain_name: str,
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

        rows.append(
            {
                "domain": domain_name,
                "match_id": match_id,
                "agent": Group68_Negotiator.__name__,
                "opponent": opponent_name,
                "repetition": repetition,
                "role": role,
                "start_order": start_order,
                "history_index": index,
                "step": int(getattr(state, "step", index)),
                "relative_time": float(getattr(state, "relative_time", 0.0)),
                "offer_repr": None if offer is None else json.dumps(list(offer)),
                "proposer_role": proposer_role,
                "our_utility_on_offer": float(our_ufun(offer)) if offer is not None else None,
                "opp_utility_on_offer": float(opp_ufun(offer)) if offer is not None else None,
                "is_agreement_offer": bool(agreement is not None and offer == agreement),
            }
        )

    return rows


def run_self_play(
    n_repetitions: int = 3,
    domain_builders: Optional[dict[str, DomainBuilder]] = None,
) -> None:
    domain_builders = domain_builders or benchmark_domains()

    for domain_name, domain_builder in domain_builders.items():
        for i in range(n_repetitions):
            issues, buyer_ufun, seller_ufun, n_steps = domain_builder()
            mechanism = SAOMechanism(issues=issues, n_steps=n_steps)

            buyer = Group68_Negotiator(name=f"{domain_name}_selfbuyer_{i + 1}", ufun=buyer_ufun)
            seller = Group68_Negotiator(name=f"{domain_name}_selfseller_{i + 1}", ufun=seller_ufun)

            mechanism.add(buyer)
            mechanism.add(seller)

            result = mechanism.run()
            agreement = extract_agreement(result)

            buyer_utility = outcome_utility(buyer.ufun, agreement)
            seller_utility = outcome_utility(seller.ufun, agreement)

            print(
                f"Self-play [{domain_name}] {i + 1}: "
                f"Agreement: {agreement}, "
                f"Buyer Utility: {buyer_utility}, "
                f"Seller Utility: {seller_utility}, "
                f"Agreement Reached: {agreement is not None}"
            )


def run_tournament(
    agents: list,
    n_repetitions: int = 5,
    return_trace: bool = False,
    domain_builders: Optional[dict[str, DomainBuilder]] = None,
):
    columns = [
        "domain",
        "agent",
        "opponent",
        "repetition",
        "role",
        "start_order",
        "our_utility",
        "opp_utility",
        "agreement",
        "nash_product",
        "social_welfare",
        "final_offer",
        "n_rounds",
        "match_id",
        "offer_sequence",
    ]
    results = []
    trace_rows = []

    domain_builders = domain_builders or benchmark_domains()

    for domain_name, domain_builder in domain_builders.items():
        for opponent_class in agents:
            if opponent_class == Group68_Negotiator:
                continue

            for i in range(n_repetitions):
                issues, buyer_ufun, seller_ufun, n_steps = domain_builder()
                role_configs = [
                    ("our_buyer", buyer_ufun, seller_ufun),
                    ("our_seller", seller_ufun, buyer_ufun),
                ]

                for role_label, our_ufun, opp_ufun in role_configs:
                    for start_order in ["our_first", "our_second"]:
                        mechanism = SAOMechanism(issues=issues, n_steps=n_steps)

                        our_agent = Group68_Negotiator(
                            name=f"agent_Group68_{domain_name}_{role_label}_{start_order}_{i + 1}",
                            ufun=our_ufun,
                        )
                        opp_agent = opponent_class(
                            name=f"{opponent_class.__name__}_{domain_name}_{role_label}_{start_order}_{i + 1}",
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
                        social_welfare = our_utility + opp_utility
                        history = mechanism.history
                        match_id = (
                            f"{domain_name}_{opponent_class.__name__}_{role_label}_"
                            f"{start_order}_rep_{i + 1}"
                        )
                        offer_sequence = [state.current_offer for state in history]

                        trace_rows.extend(
                            _build_trace_rows(
                                mechanism=mechanism,
                                domain_name=domain_name,
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

                        results.append(
                            {
                                "domain": domain_name,
                                "agent": Group68_Negotiator.__name__,
                                "opponent": opponent_class.__name__,
                                "repetition": i + 1,
                                "role": role_label,
                                "start_order": start_order,
                                "our_utility": our_utility,
                                "opp_utility": opp_utility,
                                "agreement": agreement is not None,
                                "nash_product": nash_product(
                                    our_utility,
                                    opp_utility,
                                    float(our_agent.ufun.reserved_value),
                                    float(opp_agent.ufun.reserved_value),
                                ),
                                "social_welfare": social_welfare,
                                "final_offer": None if agreement is None else json.dumps(list(agreement)),
                                "n_rounds": len(history),
                                "match_id": match_id,
                                "offer_sequence": json.dumps(offer_sequence),
                            }
                        )

    summary_df = pd.DataFrame(results, columns=columns)
    if not return_trace:
        return summary_df

    trace_df = pd.DataFrame(trace_rows)
    return summary_df, trace_df


def compute_metrics(results: pd.DataFrame) -> dict:
    if results.empty:
        return {
            "avg_utility": 0.0,
            "agreement_rate": 0.0,
            "avg_nash_product": 0.0,
            "avg_social_welfare": 0.0,
        }

    return {
        "avg_utility": float(results["our_utility"].mean()),
        "agreement_rate": float(results["agreement"].mean()),
        "avg_nash_product": float(results["nash_product"].mean()),
        "avg_social_welfare": float(results["social_welfare"].mean()),
    }


def summarize_results(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_domain_opponent = (
        results.groupby(["domain", "opponent"])
        .agg(
            matches=("agreement", "size"),
            agreement_rate=("agreement", "mean"),
            avg_our_utility=("our_utility", "mean"),
            avg_opp_utility=("opp_utility", "mean"),
            avg_nash_product=("nash_product", "mean"),
            avg_social_welfare=("social_welfare", "mean"),
            avg_rounds=("n_rounds", "mean"),
        )
        .round(3)
        .reset_index()
    )

    by_domain = (
        results.groupby("domain")
        .agg(
            matches=("agreement", "size"),
            agreement_rate=("agreement", "mean"),
            avg_our_utility=("our_utility", "mean"),
            avg_opp_utility=("opp_utility", "mean"),
            avg_nash_product=("nash_product", "mean"),
            avg_social_welfare=("social_welfare", "mean"),
        )
        .round(3)
        .reset_index()
    )

    return by_domain_opponent, by_domain


def print_summary_tables(results: pd.DataFrame) -> None:
    by_domain_opponent, by_domain = summarize_results(results)
    print("\nBy domain and opponent:")
    print(by_domain_opponent.to_string(index=False))
    print("\nDomain totals:")
    print(by_domain.to_string(index=False))


def plot_results(results: pd.DataFrame, save_path: str = "results.png") -> None:
    if results.empty:
        print("No results to plot.")
        return

    summary = (
        results.groupby(["domain", "opponent"])
        .mean(numeric_only=True)
        .reset_index()
    )
    summary["benchmark"] = summary["domain"] + "\n" + summary["opponent"]

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    summary.plot(kind="bar", x="benchmark", y="agreement", ax=axes[0, 0], title="Agreement Rate")
    summary.plot(
        kind="bar",
        x="benchmark",
        y=["our_utility", "opp_utility"],
        ax=axes[0, 1],
        title="Average Utility",
    )
    summary.plot(kind="bar", x="benchmark", y="nash_product", ax=axes[1, 0], title="Nash Product")
    summary.plot(kind="bar", x="benchmark", y="social_welfare", ax=axes[1, 1], title="Social Welfare")

    for ax in axes.flatten():
        ax.set_xlabel("Benchmark")
        ax.tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def save_readable_traces(trace: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    grouped = trace.groupby(["domain", "opponent"])
    for (domain_name, opponent_name), opponent_trace in grouped:
        sorted_trace = opponent_trace.sort_values(["repetition", "step", "history_index"])
        lines = []

        for match_id, match_trace in sorted_trace.groupby("match_id", sort=False):
            role_label = str(match_trace.iloc[0]["role"]) if "role" in match_trace.columns else "unknown"
            start_order = (
                str(match_trace.iloc[0]["start_order"])
                if "start_order" in match_trace.columns
                else "unknown"
            )
            lines.append(f"{match_id} ({role_label}, {start_order}):")
            for _, row in match_trace.iterrows():
                agreement_mark = " | AGREEMENT" if bool(row["is_agreement_offer"]) else ""
                lines.append(
                    "  "
                    f"t={float(row['relative_time']):.3f}"
                    f" | step={int(row['step'])}"
                    f" | offer={row['offer_repr']}"
                    f" | proposer={row['proposer_role']}"
                    f" | our_u={float(row['our_utility_on_offer']):.2f}"
                    f" | opp_u={float(row['opp_utility_on_offer']):.2f}"
                    f"{agreement_mark}"
                )
            lines.append("")
            lines.append("")

        output_path = output_dir / f"{domain_name}__{opponent_name}.txt"
        output_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    domain_builders = benchmark_domains()
    run_self_play(n_repetitions=3, domain_builders=domain_builders)

    opponents = [
        AspirationNegotiator,
        BoulwareTBNegotiator,
        ConcederTBNegotiator,
        RandomNegotiator,
        ToughNegotiator,
    ]
    results, trace = run_tournament(
        [Group68_Negotiator] + opponents,
        n_repetitions=5,
        return_trace=True,
        domain_builders=domain_builders,
    )
    metrics = compute_metrics(results)
    print("\nOverall metrics:", metrics)
    print_summary_tables(results)

    results_path = "tournament_results.csv"
    results.to_csv(results_path, index=False)
    print(f"\nSaved detailed results to {results_path}")

    readable_trace_dir = Path("tournament_traces")
    save_readable_traces(trace, readable_trace_dir)
    print(f"Saved readable traces to {readable_trace_dir}")

    plot_results(results, save_path="results.png")
    print("Saved plot to results.png")

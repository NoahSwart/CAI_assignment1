# Report Outline And History Summary

## Purpose

This document turns the current benchmark evidence, design notes, and git history into a report-ready story for the negotiation assignment.

It is based on:

- `tournament_results.csv`
- `extended_benchmark_results.csv`
- `EVALUATION_NOTES_2026-03-25.md`
- git history up to commit `6d6cfde`
- the current uncommitted work on branch `eval-agent-improvements`

## One-Sentence Story

Our agent started as a modular negotiator with bidding, acceptance, and opponent-model components, but multi-domain evaluation revealed a serious late-stage deadlock problem on narrow-overlap domains; after revising the deadline behavior and expanding the benchmark setup, the agent became substantially more adaptable while still showing clear weaknesses against uncompromising opponents.

## Evolution Summary From Git History

### Main development stages

1. `5d3dcee` - initial project planning
2. `b68a6f7` - shared utility helpers were added
3. `021c5b3` - the first complete `Group68_Negotiator` was assembled
4. `dff13a1` - a first tournament script was introduced
5. `0692c8c` - opponent-model basics were added
6. `7099b9b` - bidding strategy and opponent-model adjustments were added
7. `25a37f9` - more testing and opponent-focused tuning
8. `58a16f6` - standard NegMAS negotiators were added to the tournament benchmark
9. `6d6cfde` - strategy improvements aimed at outperforming imported agents

### Current branch work after the last commit

The current branch adds another phase that is not yet reflected in the committed history:

- expansion from a one-domain benchmark to a three-domain benchmark
- identification of a late-stage deadlock bug on narrow-overlap domains
- deadline-related fixes in bidding and acceptance logic
- targeted verification tests for the discovered failures
- an evidence-based rejected experiment, where a more aggressive late-settlement bidding change hurt overall robustness

This gives you a strong development narrative:

- early phase: build the agent and main modules
- middle phase: add opponent modeling and tournament evaluation
- late phase: use broader experiments to detect and fix a hidden robustness problem

## Current Best Benchmark Story

### Before broader evaluation

The original tournament harness looked acceptable on an easy single-issue toy domain, but that benchmark was misleading because it hid failures on harder domains.

### After broader evaluation

The expanded benchmark evaluated:

- 3 domains
- 5 built-in NegMAS opponents
- 5 repetitions per matchup
- both buyer/seller roles
- both start orders

### Domain-level before/after summary

- `single_issue_10`
  - agreement: `0.73 -> 0.98`
  - avg our utility: `4.770 -> 5.020`
  - avg Nash product: `9.200 -> 9.600`

- `single_issue_50_overlap`
  - agreement: `0.24 -> 0.43`
  - avg our utility: `26.830 -> 26.990`
  - avg Nash product: `0.200 -> 0.600`

- `two_issue_5x5`
  - agreement: `0.74 -> 0.74`
  - avg our utility: `2.192 -> 2.152`
  - avg Nash product: `0.312 -> 0.304`

### Main interpretation

- The most important improvement is on `single_issue_50_overlap`.
- The deadlock-prone version looked acceptable on the easy benchmark but failed badly on the more realistic overlap domain.
- After the late-stage fix, overlap-domain agreement improved substantially without harming the agent's overall identity.
- Results on `two_issue_5x5` remained broadly stable, which supports the claim that the fix improved robustness rather than simply overfitting one domain.

## What The Report Should Emphasize

### Strong claims that are supported

- The agent uses a modular design with separate bidding, acceptance, and opponent-model components.
- Opponent behavior is explicitly modeled through offer frequencies and concession-rate estimation.
- Broader evaluation changed the development direction; without multi-domain testing the main weakness would have been missed.
- The main improvement was not just higher selfish utility, but better adaptability and fewer deadlocks on harder domains.

### Honest limitations to discuss

- `ToughNegotiator` remains a major weakness.
- Some failures are structural: in harder domains, `ToughNegotiator` may keep offering outcomes below our reservation value.
- Some patient-opponent failures remain in `single_issue_50_overlap`, especially in protocol/order combinations where feasible offers arrive too late.
- `RandomNegotiator` is noisy, so small differences between runs should not be over-interpreted.

### What not to claim

- do not claim the agent is universally strong
- do not claim all remaining failures are strategy bugs
- do not claim every attempted improvement helped
- do not rely only on the toy domain as evidence

## Suggested Report Structure

This should fit well into a 5-page IJCAI-style report.

### 1. Introduction / Problem Setup

Explain the assignment briefly:

- bilateral SAOP negotiation in NegMAS
- additive utilities
- unknown opponent preferences
- need for both strong negotiation performance and adaptability across agents and domains

### 2. Agent Design

Describe the structure first:

- `on_negotiation_start` initializes the opponent model, acceptance strategy, and bidding strategy
- `propose` delegates bid generation to the bidding strategy
- `respond` updates the opponent model and decides whether to accept

Then explain the components:

- `BiddingStrategy.target_utility`
- `BiddingStrategy.get_bid`
- `AcceptanceStrategy.acceptance_threshold`
- `AcceptanceStrategy.should_accept`
- `OpponentModel.update`
- `OpponentModel.get_estimated_utility`
- `OpponentModel.get_concession_rate`
- `OpponentModel.get_opponent_style`

### 3. Experimental Setup

Describe:

- the benchmark opponents
- the three domains
- repetitions
- role swapping
- start-order variation
- metrics used: agreement rate, our utility, opponent utility, Nash product, social welfare

### 4. Results And Analysis

This should be the most important section.

Explain:

- the original benchmark was too easy
- the broader benchmark exposed the overlap-domain deadlock
- the late-stage fix improved the hard domain substantially
- some opponent/domain combinations remain difficult or impossible

### 5. Discussion / Limitations

Discuss:

- strengths against conceders and many random opponents
- improved robustness on the hard overlap domain
- persistent difficulty against uncompromising opponents
- one rejected experiment, showing that not every extra concession rule improved general performance

## Draft Paragraphs

### Draft: Agent Overview

`Group68_Negotiator` is organized as a modular negotiating agent with three main components: a bidding strategy, an acceptance strategy, and an opponent model. At the start of each negotiation, the method `on_negotiation_start` initializes these components. During the negotiation, `propose` computes the next offer through `BiddingStrategy.get_bid`, while `respond` updates the opponent model and decides whether to accept the current offer. This structure made it possible to improve the agent incrementally by changing the late-stage bidding and acceptance behavior without rewriting the entire agent.

### Draft: Opponent Model

The opponent model estimates the opponent's preferences from observed bids. It records how often issue values occur in received offers and uses this frequency information to estimate the opponent's utility for outcomes. In addition, it tracks the estimated utility of the opponent's offers over time and computes a concession rate through linear regression. This allows the agent to classify the opponent into rough styles such as conceder, late conceder, hardliner, or unknown, and to adapt its bidding and acceptance behavior accordingly.

### Draft: Original Weakness

The first version of the benchmark suggested that the agent was reasonably strong, because it performed well on a simple single-issue domain. However, after extending the evaluation to a harder single-issue overlap domain and a small two-issue domain, we found a major weakness: the agent often failed to reach agreement in domains with narrower feasible overlap. Trace inspection showed that the late-stage bidding and acceptance heuristics were too stubborn, so the agent either continued bidding above the feasible overlap or rejected acceptable deadline offers.

### Draft: Main Improvement

To address this, we revised the deadline behavior of the agent. First, the late bidding floor was changed so that it decays toward the reservation value near the deadline instead of remaining artificially high. Second, the endgame bidding curve was adjusted to concede faster after the late stage starts. Third, the final acceptance fallback was simplified so that the agent accepts any offer that is at least as good as no agreement. Finally, reservation checking was corrected from a strict comparison to a non-strict one, preventing the agent from rejecting offers exactly at the reservation value.

### Draft: Main Result

These changes substantially improved the agent's robustness on the hardest benchmark. On the `single_issue_50_overlap` domain, the overall agreement rate increased from `0.24` to `0.43`, while the average Nash product increased from `0.20` to `0.60`. This is an important result because it shows that the modified agent not only reached agreement more often, but also produced more balanced outcomes above reservation values. At the same time, performance on the two-issue domain remained broadly stable, suggesting that the change improved adaptability rather than simply overfitting a single case.

### Draft: Limitations

Despite these improvements, the agent still has clear limitations. In particular, it remains weak against `ToughNegotiator`, especially on domains where the opponent's repeated offers remain below our reservation value. In these cases, no acceptable agreement may be reachable under the protocol. We also tested a more aggressive late-settlement bidding change that allowed the agent to consider slightly more concessive offers before the deadline, but this change reduced overall robustness and was therefore rejected. This highlights that not every plausible concession heuristic improves general negotiation performance.

## Recommended Tables And Figures

### Table 1: Agent Structure

Columns:

- Component
- Main methods
- Role in negotiation

### Table 2: Benchmark Setup

Columns:

- Domain
- Issues
- Reservation values
- Opponents
- Repetitions

### Table 3: Before/After Results

At minimum include:

- domain
- agreement rate before
- agreement rate after
- avg our utility before
- avg our utility after
- Nash product before
- Nash product after

### Figure 1: Agreement Rate By Domain And Opponent

Use `results.png` or regenerate a cleaner version if needed.

### Figure 2: Utility / Social Welfare Comparison

Useful if space permits.

## Good Storyline For The Discussion Section

Use this progression:

1. We first built a modular agent with opponent-aware bidding and acceptance.
2. We initially evaluated it on a simple domain and obtained acceptable-looking results.
3. We broadened the benchmark and discovered a hidden late-stage deadlock weakness.
4. We diagnosed the cause through traces and utility-threshold analysis.
5. We revised the late-stage negotiation logic and re-ran the benchmark.
6. The agent became meaningfully more robust on the hard overlap domain.
7. We also tested an additional aggressive settlement idea, but rejected it because it harmed overall performance.

That is a much stronger report story than simply listing the final code features.

## Practical Advice For Writing The Final Report

- Center the report on the harder domain, not the toy domain.
- Use the toy domain only to show that the agent still performs well in easier conditions.
- Treat `ToughNegotiator` as an honest limitation section.
- Mention that broader testing changed the design decisions.
- Keep the strongest quantitative comparison focused on `single_issue_50_overlap`.
- If you need to cut content for page limit, cut low-value per-opponent detail before cutting the before/after story.

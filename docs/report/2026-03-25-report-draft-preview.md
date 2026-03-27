# Group 68 Negotiator: Opponent-Aware Negotiation with Multi-Domain Evaluation

**Group:** 68  
**Members:** `<fill in names here>`

## Abstract

This report presents `Group68_Negotiator`, a bilateral SAOP negotiation agent implemented in NegMAS for additive utility domains. The agent is structured around three interacting components: a bidding strategy, an acceptance strategy, and an opponent model. Our initial evaluation on a simple single-issue domain suggested that the agent was reasonably strong, but broader testing revealed a major weakness on narrower-overlap domains: the agent often deadlocked late in the negotiation even when feasible agreements existed. We therefore expanded the benchmark to multiple domains and opponents, analyzed traces and utility thresholds, and revised the agent's late-stage bidding and acceptance behavior. The resulting agent became more robust on the hardest benchmark, improving agreement rate on the `single_issue_50_overlap` domain from `0.24` to `0.43` while maintaining broadly stable performance on the two-issue benchmark. The report also discusses the remaining limitations of the agent, especially against uncompromising opponents such as `ToughNegotiator`, and shows how experimental results informed the final design.

## 1. Introduction

The assignment is to build a bilateral negotiating agent for the Stacked Alternating Offers Protocol (SAOP) in NegMAS under additive utility functions, unknown opponent preferences, reservation values, and no discounting. In this setting, a good agent should not only obtain high utility for itself, but should also remain adaptable across different domains and against different negotiation styles. This makes the task more difficult than optimizing for a single benchmark.

Our main design goal was therefore to build an agent that is modular, interpretable, and easy to improve through testing. We implemented separate modules for offer generation, acceptance decisions, and opponent modeling. This separation was useful later in development, because broader evaluation exposed a hidden weakness in the agent's late-stage behavior. We could then revise the endgame logic without redesigning the whole system.

The main lesson from our development process is that apparently good performance on a simple toy benchmark was misleading. Once we evaluated the agent across multiple domains and multiple built-in NegMAS opponents, we discovered a serious deadlock problem on narrow-overlap domains. This report focuses on that finding, the fixes we implemented, and the extent to which those fixes improved the robustness of the final agent.

## 2. Agent Design

### 2.1 High-level structure

`Group68_Negotiator` is implemented as a modular SAO negotiator. The main class is defined in `group_68_negotiator.py` and uses three helper modules:

- `bidding_strategy.py`
- `acceptance_strategy.py`
- `opponent_model.py`

At the start of a negotiation, `on_negotiation_start()` initializes the `OpponentModel`, `AcceptanceStrategy`, and `BiddingStrategy`. During the negotiation, `propose()` generates the next offer through `BiddingStrategy.get_bid()`, and `respond()` updates the opponent model and decides whether to accept or reject the current offer. This architecture made it easier to identify which part of the agent caused failures and to improve the late-game behavior in a targeted way.

### 2.2 Main Python methods

The assignment explicitly asks for the main Python methods to be described. The most important methods in our implementation are:

- `Group68_Negotiator.on_negotiation_start()`: initializes all strategy modules and resets negotiation-specific state.
- `Group68_Negotiator.propose()`: computes the next bid to send to the opponent.
- `Group68_Negotiator.respond()`: updates the opponent model, checks reservation constraints, and decides whether to accept or reject.
- `BiddingStrategy.target_utility()`: computes the target utility level at time `t` using a time-dependent concession curve.
- `BiddingStrategy.get_bid()`: finds a candidate bid close to the current target utility and optionally selects an opponent-aware bid.
- `AcceptanceStrategy.acceptance_threshold()`: computes the minimum utility we are willing to accept at time `t`.
- `AcceptanceStrategy.should_accept()`: applies threshold-based, best-seen, and opponent-aware acceptance checks.
- `OpponentModel.update()`: updates value frequencies and concession observations from a newly received offer.
- `OpponentModel.get_estimated_utility()`: estimates how attractive an outcome is for the opponent using offer frequencies.
- `OpponentModel.get_concession_rate()`: estimates how quickly the opponent is conceding using a regression slope over time.
- `OpponentModel.get_opponent_style()`: classifies the opponent as a rough style such as `conceder`, `late_conceder`, `hardliner`, or `unknown`.
- `utils.is_above_reservation()`: checks whether an outcome is at least as good as no agreement.
- `utils.nash_product()`: computes the gains above reservation for both sides.

These methods are the core of the negotiation logic and are the methods that should be highlighted in both the report and the source code comments.

### 2.3 Bidding strategy

Our bidding strategy is time dependent and opponent aware. The core idea is to start from ambitious offers near our own maximum utility and gradually concede as the deadline approaches, following ideas from the automated negotiation literature on time-dependent tactics and hybrid concession strategies [2, 3]. The method `target_utility()` computes a concession target using an adaptive exponent. This exponent is adjusted based on the estimated opponent style, so that the agent remains firmer against hardliners and concedes earlier against conceders.

The method `get_bid()` then searches the sampled outcome space for bids near the target utility. To avoid unnecessary repetition, it filters recently repeated bids. Once enough interaction data has been collected, the method `_opponent_aware_bid()` scores candidate bids using both our own utility and the opponent's estimated utility. This gives the agent a simple form of preference adaptation: when multiple bids are similarly good for us, it prefers ones that appear more acceptable to the opponent.

### 2.4 Acceptance strategy

The acceptance strategy combines a time-based aspiration threshold with opponent-aware checks. The method `acceptance_threshold()` computes a decreasing minimum acceptable utility that never falls below our reservation value. The method `should_accept()` accepts offers that satisfy this threshold and are still sufficiently favorable compared to the opponent's estimated utility. Late in the negotiation, it can also use a best-seen heuristic to accept improving offers that are close to the current threshold.

In addition to the acceptance module, the main negotiator class applies an `AC_next`-style comparison in `respond()`: if the current offer is better than what the agent expects to propose next by a sufficient margin, the offer is accepted. This hybrid design was intended to balance ambition and practicality.

### 2.5 Opponent model

The opponent model is deliberately lightweight so that it remains fast and transparent. It records how often the opponent offers specific issue values and uses these frequencies to estimate the opponent's utility for outcomes. It also stores estimated utilities over time and uses linear regression to approximate the opponent's concession rate.

This information is used in two ways. First, the bidding strategy can prefer candidate outcomes that look relatively better for the opponent. Second, the acceptance strategy can be more or less demanding depending on whether the opponent seems to be a hardliner, late conceder, or conceder. This is the main way in which our agent takes opponent preferences into account, as required by the assignment.

## 3. Experimental Setup

### 3.1 Why we changed the benchmark

The original benchmark in the repository only covered one easy single-issue domain. That setup was not sufficient to evaluate how generic the agent really was. Section 2.4 of the assignment explicitly asks us to test the agent against itself, against many other agents, and across multiple domains. We therefore expanded the benchmark to include more domains, more opponents, both role assignments, and both start orders.

### 3.2 Benchmarks

We evaluated the agent on three domains:

- `single_issue_10`: a simple 10-value single-issue price domain with reservation value `0.0` for both sides.
- `single_issue_50_overlap`: a harder 50-value single-issue price domain with narrow feasible overlap and reservation values `34.0` and `12.0`.
- `two_issue_5x5`: a two-issue domain with `price` and `delivery_time`, additive weights `(0.6, 0.4)`, and reservation value `1.2` for both sides.

We tested against the following opponents:

- `AspirationNegotiator`
- `BoulwareTBNegotiator`
- `ConcederTBNegotiator`
- `RandomNegotiator`
- `ToughNegotiator`

We also ran self-play with `Group68_Negotiator` against itself.

For each domain-opponent pair, we ran 5 repetitions in both role configurations (`our_buyer`, `our_seller`) and both start orders (`our_first`, `our_second`). This produces a more reliable picture than a single run because some outcomes, especially against `RandomNegotiator`, are noisy.

### 3.3 Metrics

We used the following metrics:

- agreement rate
- average utility for our agent
- average utility for the opponent
- average Nash product
- average social welfare
- negotiation traces and average number of rounds

We selected these metrics because the assignment asks for more than raw utility. Agreement rate measures robustness, our utility measures selfish performance, Nash product indicates whether both sides gain above reservation, and social welfare shows total efficiency. These are directly relevant to the assignment's request to analyze how close outcomes are to efficient solutions and whether the agent performs well across settings.

## 4. Results and Analysis

### 4.1 Baseline finding: the easy benchmark was misleading

The first version of the benchmark suggested that the agent was reasonably strong. On the simple `single_issue_10` domain, it achieved high agreement rates against most standard agents. However, broader testing exposed a serious weakness. On the harder `single_issue_50_overlap` domain, the pre-fix version achieved only `0.24` agreement overall and failed completely against both `AspirationNegotiator` and `BoulwareTBNegotiator`.

This was also visible in the repository's top-level demo: `main.py` originally failed to reach agreement. Trace inspection showed that the agent was too stubborn in the endgame. Its late bidding floor and late acceptance logic remained above the feasible overlap region, so it continued proposing unrealistic offers and rejected offers that were actually acceptable relative to the reservation value.

### 4.2 Diagnosing the weakness

The failure was not mainly in the early opponent model or the overall architecture. Instead, it came from the interaction between the time-dependent bidding curve and the late-stage acceptance rules. On the narrow-overlap domain, the utility thresholds close to the deadline remained too high for both buyer and seller roles. In practice, this produced artificial deadlocks even though the overlap region was reachable.

This diagnosis was important because it prevented us from making random global changes. Rather than rewriting the whole agent, we focused on the specific part of the strategy that was blocking settlement near the deadline.

### 4.3 Strategy changes

We implemented four main changes:

1. The late bidding floor in `bidding_strategy.py` now decays toward the reservation value near the deadline instead of staying artificially high.
2. The bidding target receives an additional endgame concession boost after the late stage begins.
3. The final fallback in `respond()` now accepts any offer that is at least as good as no agreement.
4. Reservation checking in `utils.py` was corrected from a strict comparison to a non-strict one, so offers exactly at reservation are no longer rejected.

These changes preserved the modular structure of the agent while directly addressing the root cause discovered in the traces.

### 4.4 Before/after benchmark summary

The strongest evidence for improvement comes from the domain totals:

| Domain | Agreement Before | Agreement After | Avg Our Utility Before | Avg Our Utility After | Nash Before | Nash After |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `single_issue_10` | 0.73 | 0.98 | 4.77 | 5.02 | 9.20 | 9.60 |
| `single_issue_50_overlap` | 0.24 | 0.43 | 26.83 | 26.99 | 0.20 | 0.60 |
| `two_issue_5x5` | 0.74 | 0.74 | 2.19 | 2.15 | 0.31 | 0.30 |

The key result is the substantial improvement on `single_issue_50_overlap`, the benchmark that originally exposed the hidden weakness. Agreement rate increased from `0.24` to `0.43`, and the average Nash product increased from `0.20` to `0.60`. These changes show that the agent became more capable of reaching feasible settlements above reservation values on difficult domains.

At the same time, performance on `two_issue_5x5` stayed broadly stable. This is important because it suggests that the new deadline behavior improved robustness rather than simply overfitting a single benchmark.

### 4.5 Opponent-level interpretation

The post-fix results show a clear pattern. The agent performs strongly against `ConcederTBNegotiator`, and it remains effective on the easy single-issue domain against both aspiration-based and boulware opponents. On the harder overlap domain, the changes improved agreement against `AspirationNegotiator` and `BoulwareTBNegotiator` from `0.00` to `0.25`, and against `ConcederTBNegotiator` from `0.50` to `1.00`.

However, the agent still fails against `ToughNegotiator` on the harder domains. This is an important limitation, but it should be interpreted carefully. In some of these runs, `ToughNegotiator` keeps offering outcomes below our reservation value while also refusing our late concessions, which means that some failures are structural rather than purely caused by a bad heuristic on our side.

Results against `RandomNegotiator` should also be interpreted cautiously. Because the opponent is stochastic, small changes between runs do not necessarily indicate a real strategic improvement or degradation.

### 4.6 Rejected experiment

After the successful deadline fix, we also tried a more aggressive late-settlement modification that widened the candidate set below the target utility near the deadline. The motivation was to improve the remaining failures against patient opponents on the overlap domain. However, this experiment did not improve the target cases enough and reduced overall robustness on other matchups, especially some random-opponent and self-play results. We therefore rejected the change.

This failed experiment is still valuable to report. It shows that our development process was evidence driven rather than purely based on adding more concessions whenever a benchmark was difficult.

## 5. Discussion, Strengths, and Limitations

The final version of the agent has three main strengths. First, it has a modular and understandable architecture, which made it possible to diagnose and fix behavior without rewriting the whole agent. Second, it explicitly takes the opponent into account through frequency-based preference estimation and concession-style classification. Third, its final benchmark performance is meaningfully more adaptable than the original version, especially on the domain that exposed the hidden deadlock weakness.

The main weakness is performance against uncompromising opponents such as `ToughNegotiator`. The agent still depends on feasible overlap emerging before the deadline, and it does not yet use a richer predictive model of what offers the opponent is likely to accept next. Another limitation is that our opponent model is intentionally simple. It is fast and robust, but it may fail to capture more subtle preference structures in multi-issue domains.

Overall, the most important conclusion is not that the final agent is universally strong. Instead, it is that broader multi-domain evaluation changed our understanding of the agent and led to a concrete, validated improvement. Without testing on harder domains and against multiple agent types, we would have overestimated the agent's generality.

## References

[1] Gerhard Weiss. *Multiagent Systems*. MIT Press, 2013.  
[2] Catholijn M. Jonker, Reyhan Aydogan, and Tim Baarslag. *Negotiating Agents*. Brightspace Resources and Tools, 2021.  
[3] Dave de Jonge. *Introduction to Automated Negotiation*. 2026.  

## Mandatory Coverage Checklist

Use this checklist when turning this draft into the final IJCAI report.

- Include the group number and all group member names.
- Keep the main report to 5 pages or less in IJCAI format, excluding references.
- Explicitly describe the negotiation setup: bilateral SAOP, additive utilities, unknown opponent preferences, reservation values, no discounting.
- Explain the high-level structure of the agent and the code organization.
- Explicitly mention the main Python methods used by the agent.
- Explain the bidding strategy, acceptance strategy, preparatory steps, and important heuristics.
- Show clearly how the agent takes the opponent's preferences into account.
- Document the tests that were run across multiple agents and multiple domains.
- Include actual scores over multiple sessions, not just one-off examples.
- Explain the testing setup: domains, opponents, repetitions, role swaps, and start-order variation.
- Explain why the chosen metrics were used.
- Include both strengths and weaknesses of the agent.
- Describe how the test results informed specific strategy changes.
- Include at least one honest limitation section and avoid over-claiming.
- Mention the rejected extra heuristic as evidence-driven iteration.
- Support strategy choices with literature and connect those references to actual design decisions.
- If you tested against agents from other groups, explicitly name and thank those groups.
- Add a short individual-contributions section at the end of the report. This part is not counted in the 5-page limit.

## Finalization Notes

Before submission, still check the following:

- convert this content into IJCAI LaTeX or Word/PDF format
- replace placeholder member names
- decide whether `results.png` should be reused directly or remade as a cleaner figure
- add one concise table for benchmark setup and one concise before/after results table
- remove any remaining debug prints from the code if present
- exclude compiled files such as `__pycache__` from the final zip
- verify the submission zip contains only source files and required resources

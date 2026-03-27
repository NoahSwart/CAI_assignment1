# Evaluation Notes - 2026-03-25

## Branch

- Created branch: `eval-agent-improvements`

## Current Project Contents

- `main.py`: simple one-domain demo that runs `Group68_Negotiator` against itself.
- `Group68_Negotiator/group_68_negotiator.py`: main negotiator wiring bidding, acceptance, and opponent modeling.
- `Group68_Negotiator/bidding_strategy.py`: time-based concession logic plus opponent-aware bid selection.
- `Group68_Negotiator/acceptance_strategy.py`: time-threshold acceptance with best-seen and opponent-aware checks.
- `Group68_Negotiator/opponent_model.py`: frequency-based opponent utility estimate and concession-style classifier.
- `Group68_Negotiator/utils.py`: utility helpers plus Pareto/Nash helper functions.
- `Group68_Negotiator/tests/test_Bidding_strategy.py`: bidding-strategy unit tests.
- `Group68_Negotiator/tests/test_tournament.py`: benchmark harness against built-in NegMAS agents.
- `tournament_traces_old/`: older trace artifacts.
- `Group68_Negotiator/__pycache__/`: compiled Python artifacts are present in the repository and should not be part of the final submission zip.

## Assignment Requirements Pulled From `CollaborativeAI_Project-Part1_Negotiation.pdf`

- Build a bilateral SAOP negotiator in NegMAS for additive utility domains.
- Evaluate against itself and as many other agents/domains as possible.
- Analyze performance quantitatively and qualitatively.
- Report design choices, important Python methods, testing setup, strengths, weaknesses, and how testing informed improvements.
- Include explicit evidence that opponent preferences are taken into account.
- Keep the report to 5 pages max excluding references, in IJCAI format.
- Remove unnecessary debug output and keep the code portable and self-contained.

## Baseline Execution

- `pytest -q`: `2 passed in 3.12s`
- `python Group68_Negotiator/tests/test_tournament.py`:
  - self-play reached agreement at `(5,)` in all 3 runs
  - saved `tournament_results.csv`
  - saved `tournament_traces/`
  - saved `results.png`
- `python main.py`:
  - no agreement reached

## Existing Tournament Harness Results

Single-issue toy domain (`price=0..9`, 10 repetitions per matchup, both roles, both start orders):

- `AspirationNegotiator`: agreement `1.00`, avg our utility `5.000`
- `BoulwareTBNegotiator`: agreement `1.00`, avg our utility `5.000`
- `ConcederTBNegotiator`: agreement `1.00`, avg our utility `8.000`
- `RandomNegotiator`: agreement `0.675`, avg our utility `6.075`
- `ToughNegotiator`: agreement `0.000`, avg our utility `0.000`

Overall toy-domain metrics from the current harness:

- avg utility: `4.815`
- agreement rate: `0.735`
- avg Nash product: `9.2`
- avg social welfare: `6.615`
- avg Pareto distance: `None` (not implemented in the current harness)

## Extended Read-Only Benchmark

I also ran a broader benchmark against the same five opponents on three domains and saved `extended_benchmark_results.csv`.

### Domain totals

- `single_issue_10`: agreement `0.73`, avg our utility `4.770`
- `single_issue_50_overlap`: agreement `0.24`, avg our utility `26.830`
- `two_issue_5x5`: agreement `0.74`, avg our utility `2.192`

### Most important per-opponent findings

- The current agent does well on the very small zero-reservation toy domain.
- It never reaches agreement with `ToughNegotiator`.
- It collapses on the more realistic `single_issue_50_overlap` domain:
  - `AspirationNegotiator`: agreement `0.00`
  - `BoulwareTBNegotiator`: agreement `0.00`
  - `ConcederTBNegotiator`: agreement `0.50`
  - `RandomNegotiator`: agreement `0.70`
  - `ToughNegotiator`: agreement `0.00`

## Root-Cause Findings

The hardest failure is reproducible on the 50-value overlap domain used by `main.py`.

### Bidding floor blocks feasible agreements

For the buyer on the 50-value domain:

- target utility at `t=1.00`: `34.00`
- late bidding floor at `t=1.00`: `39.55`

For the seller on the 50-value domain:

- target utility at `t=1.00`: `12.00`
- late bidding floor at `t=1.00`: `25.69`

These late bidding floors sit above the feasible overlap region, so the agent does not concede far enough before the deadline.

### Late acceptance floor also blocks feasible agreements

For the buyer at `t=1.00`:

- base acceptance threshold: `34.00`
- late minimum after extra floor logic: `41.50`

For the seller at `t=1.00`:

- base acceptance threshold: `12.00`
- late minimum after extra floor logic: `30.50`

So even late in the negotiation, the extra acceptance floor can still reject offers that are above reservation and inside the feasible overlap.

### Practical interpretation

- On narrow-overlap domains, the current agent is too stubborn in both bidding and late acceptance.
- The current benchmark harness therefore overestimates generality because it focuses on one easy toy domain.

## Recommended Improvement Direction

Recommended first:

- Rework late-stage bidding and acceptance so they are domain-sensitive and never rule out the feasible overlap near deadline.
- Extend the tournament harness to multiple domains and compute agreement-only utilities, Nash, social welfare, and Pareto-distance-style efficiency.
- Add targeted regression tests for narrow-overlap domains, `main.py`-style self-play, and late-deadline behavior.

Lower-priority after that:

- Revisit opponent-style thresholds only after the late-floor bug is fixed.
- Improve trace logging so the actual acceptance point is recorded cleanly.

## Implemented Changes

The following changes have now been implemented:

- In `bidding_strategy.py`, the late bidding floor now decays toward reservation by the deadline instead of staying artificially high.
- In `bidding_strategy.py`, the target utility now gets an extra endgame concession boost after `t >= 0.85`.
- In `group_68_negotiator.py`, the final-deadline acceptance fallback now accepts any offer that is at least as good as no agreement.
- In `group_68_negotiator.py`, the late-accept trigger was moved from `0.96` to `0.95` so 20-step domains actually reach the deadline fallback.
- In `utils.py`, reservation checking was corrected from strict `>` to `>=`.
- In `Group68_Negotiator/tests/test_tournament.py`, the benchmark harness was expanded from one toy domain to three domains with per-domain summaries.
- Added targeted verification test: `Group68_Negotiator/tests/test_negotiation_behavior.py`

## Post-Fix Verification

- `pytest -q`: `4 passed in 3.06s`
- `python main.py`:
  - agreement reached at `(13,)`
  - buyer utility `36.0`
  - seller utility `13.0`
- `python Group68_Negotiator/tests/test_tournament.py`:
  - self-play now reaches agreement on all three benchmark domains
  - benchmark completes and writes refreshed `tournament_results.csv`, `results.png`, and `tournament_traces/`

## Post-Fix Benchmark Results

Current harness setup:

- 3 domains
- 5 built-in opponents
- 5 repetitions per matchup
- both roles
- both start orders

### Domain totals after the fix

Latest kept-version rerun:

- `single_issue_10`: agreement `0.98`, avg our utility `5.020`
- `single_issue_50_overlap`: agreement `0.43`, avg our utility `26.990`
- `two_issue_5x5`: agreement `0.74`, avg our utility `2.152`

### Key after-fix opponent results on `single_issue_50_overlap`

- `AspirationNegotiator`: agreement `0.25`, avg our utility `23.25`
- `BoulwareTBNegotiator`: agreement `0.25`, avg our utility `23.25`
- `ConcederTBNegotiator`: agreement `1.00`, avg our utility `25.00`
- `RandomNegotiator`: agreement `0.65`, avg our utility `40.45`
- `ToughNegotiator`: agreement `0.00`, avg our utility `23.00`

### Before/after comparison on `single_issue_50_overlap`

- overall agreement rate improved from `0.24` to `0.43`
- overall average utility improved from `26.83` to `26.99`
- `AspirationNegotiator` improved from `0.00` to `0.25` agreement rate
- `BoulwareTBNegotiator` improved from `0.00` to `0.25` agreement rate
- `ConcederTBNegotiator` improved from `0.50` to `1.00` agreement rate
- `RandomNegotiator` changed from `0.70` to `0.65`; this should be treated as noisy rather than a strong trend
- `ToughNegotiator` stayed at `0.00`

### Additional note on `ToughNegotiator`

- `single_issue_10` agreement rate improved to `1.00`, but these agreements happen at our reservation level and are not strong outcomes for us.
- `single_issue_50_overlap` and `two_issue_5x5` remain at `0.00` because `ToughNegotiator` keeps offering outcomes that are below our reservation value while also refusing our late concessions.
- This is worth explaining in the report as a limitation of the current strategy and, in some domains, a structural limitation of negotiating against an uncompromising opponent with incompatible reservation constraints.

## Additional Experiment That Was Tried And Rejected

After the successful late-stage fixes, I also tried a more aggressive late-settlement bidding change:

- widen the candidate set below the current target near the deadline
- let opponent-aware bidding choose slightly more concessive offers earlier against patient opponents

Why it looked promising:

- the remaining `AspirationNegotiator` / `BoulwareTBNegotiator` failures on `single_issue_50_overlap` appear to miss feasible settlement offers by one move near the deadline

What happened in practice:

- it did **not** improve the target failing case enough to justify keeping it
- it reduced performance on other benchmarks, especially some `RandomNegotiator` results and self-play quality

Decision:

- the change was reverted
- we kept the simpler, better-performing late-stage policy

Report value:

- this is still useful to mention briefly in the report as an example of evidence-driven iteration: not every plausible concession change improved general performance

## Current Practical Conclusion

What is worth emphasizing in the report:

- the major, validated improvement is the fix for the narrow-overlap deadlock
- multi-domain evaluation was necessary to discover and verify that weakness
- the agent is now stronger and more adaptable than the original version, but still has clear limitations against uncompromising or protocol-favored patient opponents

What is not worth over-claiming:

- that `ToughNegotiator` is solved
- that every extra concession heuristic helps
- that one benchmark run is exact, because `RandomNegotiator` introduces noise between runs

## Current Interpretation

- The late-stage deadlock on narrow-overlap domains is partially fixed.
- The agent is now materially more generic than the original version because it can settle the `main.py` domain and performs better on the harder overlap benchmark.
- `ToughNegotiator` remains the clearest unresolved weakness and should be discussed honestly in the report.
- The easy toy domain still looks good, but the report should center the multi-domain benchmark instead of the toy domain alone.

## Report Checklist

- Explain the agent structure and explicitly mention the main methods:
  - `on_negotiation_start`
  - `propose`
  - `respond`
  - `target_utility`
  - `get_bid`
  - `acceptance_threshold`
  - `should_accept`
  - `update`
  - `get_estimated_utility`
  - `get_concession_rate`
  - `get_opponent_style`
- Describe the concession strategy, acceptance strategy, opponent model, and any late-stage heuristics.
- Report baseline results on multiple domains, not only the toy domain.
- Include strengths:
  - strong results vs aspiration/boulware on the toy domain
  - high utility vs conceder and many random-agent agreements
- Include weaknesses:
  - no agreement in `main.py`
  - zero agreement vs `ToughNegotiator`
  - severe failure on narrow-overlap 50-value domains
- Show how test results motivated changes to the strategy.
- Include graphs/tables and explain what each metric means.
- Add literature support for any acceptance/concession/opponent-model strategy claims.

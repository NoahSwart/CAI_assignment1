# Agent Improvement And Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the negotiator's late-stage behavior on narrow-overlap domains and expand evaluation/report artifacts so the assignment evidence is based on multiple opponents and domains.

**Architecture:** Keep the current agent structure intact and change only the late-stage bidding/acceptance heuristics that are causing deadlocks. Extend the existing tournament harness rather than creating a separate benchmark framework, so the evaluation and report stay tied to the project’s current code layout.

**Tech Stack:** Python 3.11, NegMAS 0.15.1.post1, pytest, pandas, matplotlib

---

## File Structure

- Modify: `Group68_Negotiator/group_68_negotiator.py`
  Purpose: adjust late acceptance behavior and any negotiator-level deadline heuristics.
- Modify: `Group68_Negotiator/bidding_strategy.py`
  Purpose: make late bidding behavior concede enough to reach feasible overlap near deadline.
- Modify: `Group68_Negotiator/tests/test_tournament.py`
  Purpose: expand evaluation to more than one domain and expose report-ready metrics/results.
- Update: `EVALUATION_NOTES_2026-03-25.md`
  Purpose: record new findings for the report section.
- Generated during verification:
  - `tournament_results.csv`
  - `results.png`
  - `tournament_traces/`
  - `extended_benchmark_results.csv`

### Task 1: Fix Late-Stage Negotiation Behavior

**Files:**
- Modify: `Group68_Negotiator/bidding_strategy.py`
- Modify: `Group68_Negotiator/group_68_negotiator.py`
- Optional verification-only helper: reuse `main.py` and inline Python commands

- [ ] **Step 1: Reproduce the narrow-overlap failure before editing code**

Run:

```bash
python main.py
```

Expected:

- `No agreement reached.`

- [ ] **Step 2: Reproduce the current benchmark weakness on the 50-value overlap domain**

Run:

```bash
python -c "import pandas as pd; print(pd.read_csv('extended_benchmark_results.csv').query(\"domain == 'single_issue_50_overlap'\").groupby('opponent')['agreement'].mean())"
```

Expected:

- zero agreement against `AspirationNegotiator`
- zero agreement against `BoulwareTBNegotiator`
- zero agreement against `ToughNegotiator`

- [ ] **Step 3: Implement the minimal late-stage strategy change**

Change:

- reduce or reshape the late bidding floor in `BiddingStrategy._late_utility_floor`
- revise the negotiator-level late acceptance floor in `Group68_Negotiator.respond`
- preserve reservation-value safety, but stop blocking feasible agreements near deadline

- [ ] **Step 4: Verify the hard domain improves**

Run:

```bash
python main.py
```

Expected:

- an agreement is now reached on the overlap domain, or at minimum behavior is materially closer to agreement than before

- [ ] **Step 5: Verify no obvious baseline regression**

Run:

```bash
pytest -q
```

Expected:

- existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add Group68_Negotiator/bidding_strategy.py Group68_Negotiator/group_68_negotiator.py
git commit -m "Adjust late-stage negotiation thresholds"
```

### Task 2: Expand Evaluation Harness

**Files:**
- Modify: `Group68_Negotiator/tests/test_tournament.py`

- [ ] **Step 1: Write the evaluation change against the existing harness**

Add:

- multiple benchmark domains
- reusable domain builders
- clearer per-domain summary output
- metrics that are usable in the report

- [ ] **Step 2: Run the harness to verify it executes**

Run:

```bash
python Group68_Negotiator/tests/test_tournament.py
```

Expected:

- benchmark completes without crashing
- results are saved to CSV/plot/trace outputs
- summary includes per-domain and per-opponent comparisons

- [ ] **Step 3: Inspect whether the metrics support the report**

Check:

- agreement rate
- our utility
- opponent utility
- Nash product
- social welfare
- any efficiency metric the harness can compute reliably

- [ ] **Step 4: Commit**

```bash
git add Group68_Negotiator/tests/test_tournament.py
git commit -m "Expand negotiation benchmark coverage"
```

### Task 3: Record Report-Ready Findings

**Files:**
- Modify: `EVALUATION_NOTES_2026-03-25.md`
- Review generated artifacts in the repository root

- [ ] **Step 1: Rerun the final benchmark set**

Run:

```bash
pytest -q
python Group68_Negotiator/tests/test_tournament.py
python main.py
```

Expected:

- tests pass
- benchmark outputs refresh successfully
- demo behavior reflects the strategy changes

- [ ] **Step 2: Update the worklog with final numbers**

Add:

- before/after comparison for the 50-value overlap domain
- strongest and weakest opponents
- any remaining deadlock cases
- bullet points for the report’s evaluation and discussion sections

- [ ] **Step 3: Confirm submission hygiene**

Check:

- no compiled artifacts are intended for the final zip
- source files and required resources only
- report references the actual benchmark setup used

- [ ] **Step 4: Commit**

```bash
git add EVALUATION_NOTES_2026-03-25.md
git commit -m "Document agent evaluation findings"
```

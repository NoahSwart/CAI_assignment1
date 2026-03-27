# Agent Improvement Design

**Date:** 2026-03-25

## Goal

Improve `Group68_Negotiator` so it remains competitive on the existing easy benchmark but stops deadlocking on narrower-overlap domains, and produce benchmark/report artifacts that align with the assignment PDF.

## Current Context

The repository currently contains:

- a negotiator implementation split across bidding, acceptance, and opponent-model components
- a small tournament harness in `Group68_Negotiator/tests/test_tournament.py`
- a top-level `main.py` demo domain

The current harness only evaluates one easy single-issue domain. Baseline results show that the agent performs reasonably on that toy domain but fails to reach agreement in `main.py` and performs poorly on a harder 50-value overlap domain.

## Problem Statement

The existing late-stage heuristics are too rigid on narrow-overlap domains:

- late bidding floors keep offers above the feasible overlap near the deadline
- late acceptance floors reject offers that are above reservation and still within a feasible agreement region

This produces artificial deadlocks against patient opponents and makes the current benchmark overstate the agent's generality.

## Constraints

- Stay within the current architecture instead of redesigning the whole agent.
- Keep the work aligned with the assignment PDF:
  - evaluate on multiple domains and multiple opponents
  - analyze results quantitatively and qualitatively
  - document how testing informed strategy changes
- Do not spend time on a full regression-test expansion unless it becomes necessary to validate a specific fix.

## Options Considered

### Option 1: Minimal threshold patch

Reduce the current late floors by tuning constants only.

Pros:

- fastest change
- low code churn

Cons:

- fragile
- likely to overfit one domain
- weak report story

### Option 2: Domain-aware late-game adaptation

Keep the current architecture, but make late bidding and acceptance depend more carefully on utility span above reservation so narrow-overlap domains remain reachable near deadline.

Pros:

- fixes the identified root cause directly
- preserves current component structure
- gives a defensible report narrative

Cons:

- requires retuning both bidding and acceptance together
- still heuristic rather than theoretically optimal

### Option 3: Larger strategy rewrite

Replace both bidding and acceptance with a new overlap/efficiency-driven strategy.

Pros:

- potentially stronger

Cons:

- too risky for the assignment timeline
- harder to validate and explain

## Chosen Approach

Choose Option 2.

The implementation will:

1. keep the current component boundaries
2. revise the late bidding floor and late acceptance logic so they stop blocking feasible agreements near the deadline
3. expand benchmarking to multiple domains so generality is measured rather than assumed
4. save structured results and notes that can feed directly into the report

## Affected Files

- Modify: `Group68_Negotiator/group_68_negotiator.py`
- Modify: `Group68_Negotiator/bidding_strategy.py`
- Modify: `Group68_Negotiator/tests/test_tournament.py`
- Update notes/artifacts:
  - `EVALUATION_NOTES_2026-03-25.md`
  - generated CSV/plot/trace outputs as needed

## Verification Strategy

- rerun `pytest -q`
- rerun the tournament harness
- rerun the harder multi-domain benchmark
- compare agreement rate and utility by opponent/domain, especially on the 50-value overlap domain and against `ToughNegotiator`

## Report Impact

The report should be able to claim:

- what the original weakness was
- how it was discovered experimentally
- what strategy change was made
- how the change affected outcomes across domains and opponents

The report should not rely only on the easy toy benchmark.

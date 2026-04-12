# Plan Template

## Summary

- What is changing
- Why it is changing now
- What stays out of scope

## Current State

- Current ownership and data flow
- Current workflow or substep contract
- Known risks in the current structure

## Target State

- Intended ownership after the change
- Interfaces or identifiers that change
- Runtime vs persisted impact

## Constraints And Invariants

- Must preserve
- Must not change in this work
- Migration or compatibility constraints

## Phase Gates

- Phase 1
  - Purpose:
  - Entry conditions:
  - Exit conditions:
  - Coexistence rules:
- Phase 2
  - Purpose:
  - Entry conditions:
  - Exit conditions:
  - Coexistence rules:

## PR Slices

| PR  | Phase   | Goal | Main Changes | Non-Goals | Merge Safety | Validation |
| --- | ------- | ---- | ------------ | --------- | ------------ | ---------- |
| PR1 | Phase 1 |      |              |           |              |            |
| PR2 | Phase 1 |      |              |           |              |            |

## Coexistence / Merge Safety

- Which path remains authoritative after each PR
- Temporary adapters, shims, or dual-path rules
- Expected conflict surfaces and why the sequence is safe

## Test Plan

- Unit
- Integration
- E2E

## Risks And Open Questions

- Main regression risks
- Follow-up items that are intentionally deferred

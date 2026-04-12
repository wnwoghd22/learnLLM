# Issue Template

## Summary

- One-paragraph summary for the project issue
- Why this work exists now

## Goal

- The target outcome after all phases land

## Non-Goals

- Explicitly deferred work
- Cleanup or follow-ups that should not expand this issue

## Risks / Blockers

- Main technical risks
- Product or workflow dependencies

## Phase Gates

- [ ] Phase 1. Gate name
  - Entry conditions:
  - Exit conditions:
  - Coexistence rules:
- [ ] Phase 2. Gate name
  - Entry conditions:
  - Exit conditions:
  - Coexistence rules:

## PR Slices By Phase

- [ ] PR1: title
  - Phase:
  - Goal:
  - Depends on:
  - Merge safety:
  - Validation:
- [ ] PR2: title
  - Phase:
  - Goal:
  - Depends on:
  - Merge safety:
  - Validation:

## Merge Safety Notes

- Which old/new paths must coexist temporarily
- Which PR flips write authority or workflow authority
- Which cleanup is intentionally deferred until after the switch

## Validation Checklist

- [ ] Unit coverage updated where the contract changes
- [ ] Integration coverage updated for scene/store boundaries
- [ ] E2E or workflow coverage updated for navigation/step changes
- [ ] Manual smoke completed for the main user flow

## Done Criteria

- [ ] Main behavior moved to the intended owner
- [ ] Old workflow/UI paths removed or retired
- [ ] Tests and docs updated
- [ ] Remaining follow-ups are explicitly split into separate issues/PRs

## Related Docs / Issues

- Plan doc:
- Related issue:
- Related PRs:

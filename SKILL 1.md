---
name: change-planning
description: Plan large code changes before implementation. Use when the user asks for a detailed implementation plan, a decision-complete refactor plan, or to split a change into safe PR-sized slices across scenes, steps, stores, APIs, or workflows.
---

# Change Planning

Produce implementation-ready planning documents for large changes in this repo.

## When To Use

- The user asks for a detailed plan before coding.
- The user asks to split a refactor into reviewable PRs.
- The change crosses scene/step/store/workflow boundaries.
- The change has migration risk, persistence risk, or broad test impact.

## Required Workflow

1. Ground the plan in current code, not assumptions.
   - Read the main entrypoints, nearby stores, tests, and docs first.
   - Prefer the nearest current implementation over older note files when they conflict.
2. Define the change boundary.
   - State the current behavior.
   - State the target behavior.
   - State explicit non-goals so the implementer does not broaden scope mid-PR.
3. Identify contracts and invariants.
   - Call out affected public types, store shapes, workflow/substep ids, scene ownership, persistence, i18n, and test contracts.
   - Separate persisted contract changes from runtime-only refactors.
4. Produce a decision-complete implementation plan.
   - Name the main subsystems to touch.
   - Describe the intended data flow and ownership after the change.
   - Record edge cases, reset/undo-hydrate behavior, and backward-compat expectations when relevant.
   - Distinguish phase gates from PR slices; do not let them collapse into the same structure.
5. Produce an issue-ready execution tracker in parallel with the detailed plan.
   - Compress the architecture/spec output into a concise execution artifact that can be pasted into a project issue.
   - Organize work by ordered phase gates and finer-grained PR-sized checklist items.
   - Include goal, non-goals, dependencies, validation, and done criteria.
6. Split the work into safe PR slices.
   - Each PR must have one primary concern.
   - For each PR, include goal, main edits, explicit non-goals, dependencies, risk, and validation.
   - Prefer isolating contract changes, runtime extraction, UI wiring, and test backfills unless coupling makes that unsafe.
   - Explain why the PR can merge safely while the old and new paths coexist.
7. Map test impact.
   - Name relevant `packages/cad-app/tests/unit`, `tests/integration`, and `tests/e2e/specs` coverage.
   - If coverage is missing, say where a new focused test should go.
8. Run a conflict analysis before finalizing slices.
   - Identify likely merge-conflict or process-conflict surfaces: scene ownership, workflow routing, write authority, hydrate/persist assumptions, selectors/tests/docs.
   - Use that analysis to split PRs more finely than the phase structure when needed.

## Output Contract

- Default output doc paths:
  - Detailed plan: `docs/personal-notes/<owner>/<topic>-plan.md`
  - Issue-ready execution tracker: `docs/personal-notes/<owner>/<topic>-issue.md`
- When the user asks for Korean documentation, create a separate sibling companion doc instead of mixing languages in one file.
  - Recommended naming: `<topic>-plan.ko.md` and `<topic>-issue.ko.md`
  - Keep section order aligned with the source doc.
  - Preserve technical identifiers such as step ids, store names, scene names, and file paths in their original form.
- Use this section order for the plan doc unless the task is unusually small:
  - Summary
  - Current State
  - Target State
  - Constraints And Invariants
  - Phase Gates
  - PR Slices
  - Coexistence / Merge Safety
  - Test Plan
  - Risks And Open Questions
- Use this section order for the issue doc:
  - Summary
  - Goal
  - Non-Goals
  - Risks / Blockers
  - Phase Gates
  - PR Slices By Phase
  - Merge Safety Notes
  - Validation Checklist
  - Done Criteria
  - Related Docs / Issues
- Prefer short bullets and concrete file paths.
- Name exact workflow/substep/store identifiers when the change touches navigation or persistence.
- Every PR slice must state what it does not do.
- Every phase gate must include entry conditions, exit conditions, and coexistence rules.
- Every issue-doc phase must map to integration readiness work, not generic coordination filler.
- Every PR listed in the plan doc must appear in the issue doc as a separately trackable checklist item.
- Treat `phase count == PR count` as a smell for non-trivial changes; either split PRs further or justify why the equality is safe.
- Do not generate a Korean companion doc by default; add it only when the user explicitly asks.

## Repo-Specific Checks

- For `packages/cad-app`, include i18n impact if UI text or step labels move.
- If step or substep behavior changes, inspect the workflow store and relevant E2E navigation coverage.
- If scene ownership moves, inspect scene-manager/runtime bindings, reset/undo wiring, and hydration behavior.
- If store shape or persisted semantics change, call out whether `versioning-migration` is needed.
- If docs are part of the implementation, update the nearest guide or README after code lands; planning docs stay in `docs/personal-notes/` unless the user asks for an official guide.

## PR Slicing Rules

- Start with the smallest slice that creates a stable seam.
- Prefer separate PRs for seam creation, coexistence wiring, authority switch, dead-path cleanup, and tests/docs backfill.
- Do not mix broad cleanup into a behavior-moving PR.
- Keep risky behavior changes behind prior extraction or adapter PRs when possible.
- Prefer a final polish/docs/test PR over sprinkling low-signal cleanup across earlier slices.
- If a single PR would require reviewers to reason about more than one ownership move, split it.
- If a PR changes the authoritative writer for state or workflow, isolate that switch from surrounding cleanup when possible.

## Reference

- For a reusable planning template, open `references/plan-template.md`.
- For an issue-friendly execution template, open `references/issue-template.md`.

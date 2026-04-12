---
name: debug-fsm
description: Hypothesis-driven FSM debugging protocol that enforces evidence-based root cause analysis and guards against confirmation bias. Run only on explicit slash command invocation.
---

# Debug FSM

Structured debugging protocol for state machine (FSM) bugs in the interaction event handler. Designed to prevent confirmation bias by enforcing hypothesis enumeration, evidence-based elimination, and mandatory disconfirmation checks before concluding a root cause.

## Trigger Policy

- Run only on explicit `/debug-fsm` invocation.
- Do not auto-trigger from bug keywords. For general error handling, use `/error-protocol` instead.

## Workflow

### Phase 1: Symptom Documentation

Create a structured symptom record before any investigation:

```
## Symptom Record
- **Observed behavior**: (what actually happens)
- **Expected behavior**: (what should happen)
- **Reproduction steps**: (numbered steps to reproduce)
- **Frequency**: (always / intermittent / rare)
- **Affected states**: (which FSM states are involved)
- **Affected tools**: (which tools trigger the bug)
- **Environment**: (browser, input device, OS if relevant)
```

Do not skip this phase. Vague symptoms lead to vague hypotheses.

### Phase 2: Hypothesis Brainstorm

Enumerate **all plausible causes** without filtering or ranking. Minimum 3 hypotheses required. Each gets an ID.

```
- H1: <description>
- H2: <description>
- H3: <description>
- ...
```

Rules:

- Do not dismiss any hypothesis at this stage.
- Include hypotheses that feel unlikely — they often reveal blind spots.
- Consider categories: state transition gaps, cleanup omission, exception paths, timing/ordering, external component internal state, multi-pointer scenarios, tool switch during active interaction.

### Phase 3: Evidence Gathering

For **each** hypothesis, collect supporting and contradicting evidence with code references (`file:line`).

```
### H1: <description>
- **Supporting**: <evidence with file:line>
- **Contradicting**: <evidence with file:line>

### H2: <description>
- **Supporting**: <evidence with file:line>
- **Contradicting**: <evidence with file:line>
```

**Anti-bias rule**: For whichever hypothesis currently feels most likely, you MUST actively search for at least one piece of contradicting evidence before proceeding. If you cannot find contradicting evidence, explicitly document that you tried and what you searched for.

### Phase 4: Hypothesis Ranking

Classify each hypothesis based on evidence weight:

| ID  | Hypothesis | Status                                     | Confidence      | Key Evidence |
| --- | ---------- | ------------------------------------------ | --------------- | ------------ |
| H1  | ...        | confirmed / likely / unlikely / eliminated | high/medium/low | ...          |

- **confirmed**: direct code evidence proves this is the cause
- **likely**: strong supporting evidence, no strong contradiction
- **unlikely**: weak support or strong contradiction exists
- **eliminated**: definitive contradiction found

### Phase 5: Targeted Investigation

Deep-dive into the top 1-2 hypotheses:

1. **Trace the exact execution path** through the FSM for the reproduction scenario.
2. **Insert debug logs** (console.warn with `[DEBUG-FSM]` prefix) at critical decision points to capture runtime evidence. No logic changes.
3. **Run the FSM Audit Checklist** (below) for the specific states involved.
4. If logs are needed, add them and ask the user to reproduce the bug and report the console output.

### Phase 6: Root Cause Confirmation

Before declaring a root cause:

- [ ] The root cause explains ALL observed symptoms, not just some.
- [ ] The root cause explains why the bug is intermittent (if it is).
- [ ] At least one alternative hypothesis has been explicitly eliminated with evidence.
- [ ] If debug logs were added, the log output confirms the hypothesis.
- [ ] The proposed fix addresses the root cause, not just the symptom.

Only after these checks pass, proceed to propose a fix.

### Phase 7: Session Documentation

Save a session file to `docs/debugging/sessions/` with:

```
## Session: <date>-<short-description>
- **Status**: open | resolved | parked
- **Symptom**: <one-line summary>
- **Root Cause**: <one-line summary>
- **Hypotheses**: <list with final status>
- **Fix**: <description or PR link>
- **Evidence**: <key log output or code references>
```

---

## FSM Audit Checklist

Run this checklist for each state involved in the bug:

### Controls Enable/Disable Pairing

- [ ] Every `controls.enabled = false` in `onPointerDown` has a matching `controls.enabled = true` in:
  - `onPointerUp`
  - `onPointerCancel`
  - `onExit`
  - `onKeyDown` (Escape handler, if applicable)
- [ ] No conditional branch in `onPointerUp` can skip the `controls.enabled = true` restoration.

### Pointer Capture Pairing

- [ ] Every `requestPointerCapture(pointerId)` has a matching `releasePointerCapture(pointerId)` in:
  - `onPointerUp`
  - `onPointerCancel`
  - `onExit`

### Exception Safety

- [ ] If an exception occurs between `controls.enabled = false` and the matching `true`, is there a catch or finally block?
- [ ] Check the core `dispatch` function for try/catch around state handler calls.

### Internal State Reset

- [ ] After re-enabling controls, does the code also reset the controls' internal drag state (`_state`, `state` properties)?
- [ ] Compare with `ArchDividerState.restoreControls()` and `ArchCurveState.clearHandleInteraction()` which do reset `_state` via `Reflect.set`.

### State Transition Cleanup

- [ ] Does `onExit` clean up ALL side effects (controls, pointer capture, cursor, tool switch lock)?
- [ ] Can a tool switch occur while controls are disabled, bypassing the `onPointerUp` cleanup path?

### Multi-Pointer Safety

- [ ] If a second pointer arrives while the first is active, does the state handle it correctly?
- [ ] Does `onPointerUp` check `pointerId` before restoring controls?

---

## Key Codebase References

- **Core runtime**: `packages/cad-app/src/hooks/interaction-event-handler/useInteractionEventHandlerCore.ts`
- **States**: `packages/cad-app/src/hooks/interaction-event-handler/states/`
- **Types**: `packages/cad-app/src/types/interactionEventHandler.ts`
- **Pointer gesture utils**: `packages/cad-app/src/hooks/interaction-event-handler/utils/pointerGesture.ts`
- **Safety reset**: `useInteractionEventHandlerCore.ts` — `safetyReset` function
- **Reference implementation for controls reset**: `states/arch/ArchDividerState.ts` — `restoreControls` method

## Quality Bar

- Never conclude a root cause without checking at least one alternative hypothesis.
- Never skip Phase 2 (hypothesis brainstorm) — jumping straight to "I think it's X" is the definition of confirmation bias.
- Every hypothesis must have at least one evidence entry (supporting or contradicting) before ranking.
- Debug logs must use `[DEBUG-FSM]` prefix for easy cleanup.
- Do not modify logic until Phase 6 confirmation checks all pass.
- Session file must exist in `docs/debugging/sessions/` before declaring resolved.

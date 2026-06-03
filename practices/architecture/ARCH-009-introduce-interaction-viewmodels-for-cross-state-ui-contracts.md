---
id: ARCH-009
title: Introduce interaction ViewModels for cross-state UI contracts
domain: architecture
type: pattern
status: active
version: 1
created: 2026-06-02
updated: 2026-06-02
tags: [architecture, frontend, ui, viewmodel, interaction-contracts, testing]
aliases:
  - ARCH-009
  - interaction ViewModel
  - UI action availability contract
  - testable frontend interaction model
related: [ARCH-001, ARCH-005, ARCH-007, GOV-002]
applies_when:
  - UI action availability depends on multiple domain states or workflow states
  - JSX conditions are duplicating business interaction rules
  - a dashboard or panel must preserve actions across empty, loaded, error, and manual states
  - frontend fixes keep breaking different branches of the same user flow
review_required: false
provenance: "Harvested from token-panic on 2026-06-02, where ChatGPT/Codex dashboard actions were lost because provider state, workflow state, and JSX branches encoded the interaction contract implicitly."
---

## Principle

When UI actions become cross-state contracts, introduce a small interaction ViewModel before reaching for a larger frontend framework.

## Rationale

Some UI bugs are not caused by missing components or weak styling. They happen because action availability, fallback paths, and panel state are encoded implicitly across hooks, booleans, and JSX branches. A local fix can make one state look correct while breaking another state's entry point.

An interaction ViewModel makes the contract explicit: given domain summaries and workflow state, it returns the actions, card variants, and display-ready interaction state the UI must render. Because it is a pure function, it can be tested without a browser or component test harness.

## Guidance

Use this pattern when:

- a user-facing action must remain available across multiple states, such as empty, loaded, stale, error, manual-required, or diagnostics-required;
- multiple providers or resources share a dashboard but have different refresh, edit, or capture semantics;
- UI code starts asking business questions such as "should this action exist?" in multiple JSX branches;
- regressions show that fixing one visible branch removes another expected action.

Shape the ViewModel around interaction semantics, not component implementation details:

```ts
type DashboardActionId =
  | 'refresh_deepseek'
  | 'open_settings'
  | 'quick_capture_chatgpt'
  | 'manual_input_chatgpt';

interface DashboardViewModel {
  headerActions: DashboardActionId[];
  balanceProvider: BalanceCardVM;
  limitProvider: LimitCardVM;
}
```

Keep the ViewModel small:

- input: domain summaries, explicit workflow state, and feature flags if needed;
- output: action ids, card variants, disabled reasons, labels, and high-level UI state;
- no DOM access, no IPC calls, no side effects, no formatting that belongs in lower domain summaries.

Test the interaction contract directly:

- required actions remain present before and after data exists;
- independent provider states do not overwrite each other;
- empty, loaded, error, and manual-required states map to the intended card variants;
- adding a new action or state requires updating the ViewModel tests.

## Watch Out For

Do not use a ViewModel to duplicate domain derivation. If the UI needs business meaning such as quota health, burn rate, confidence, or warning state, derive that in the domain summary first and let the ViewModel decide presentation and actions.

Do not introduce Redux, Zustand, XState, React Router, or a UI component framework just because JSX looks busy. First identify the missing boundary:

- mutually exclusive local views: use a discriminated union;
- cross-state action availability: use a ViewModel;
- complex shared writes: consider a reducer or store;
- concurrent async transitions with cancellation/retry: consider a state machine;
- URL/deep-link/history requirements: consider a router;
- visual consistency/accessibility scale: consider a component framework.

## Example

In token-panic, ChatGPT/Codex started as manual input plus Safari assisted capture. The dashboard had to show both "Safari read/update" and "manual input/edit" when no data existed and after data was saved. Encoding that in JSX branches caused actions to disappear after refactors. A `toDashboardViewModel()` function made the action contract explicit and testable.

## Activation

- Tier: task_router
- Phases: architecture_review, before_edit, verification
- Signals: UI actions disappear across states; dashboard or panel has provider-specific actions; JSX conditionals encode workflow rules; user flow depends on preserving actions after empty/loaded/error/manual states; considering frontend framework due to interaction-state confusion
- Evidence: final report identifies the interaction contract boundary, the chosen ViewModel or smaller mechanism, and the tests that protect action availability

## Related Practices

- [[ARCH-001]]
- [[ARCH-005]]
- [[ARCH-007]]
- [[GOV-002]]

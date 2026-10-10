---
id: COLLAB-012
title: Review handoff needs both issue and PR surfaces
domain: agent-collaboration
type: checklist
status: active
version: 11
created: 2026-06-07
updated: 2026-06-18
tags: [agent-collaboration, review, handoff, github, pull-requests, human-gate, thread-tools]
aliases:
  - COLLAB-012
  - dual-surface review handoff
  - issue and PR review handoff
  - human decision contract
  - needs human contract
  - reviewer dispatch prompt
  - reviewer thread tool fallback
  - source thread callback
related: [COLLAB-002, COLLAB-007, COLLAB-008, COLLAB-009]
applies_when:
  - Architect requests changes on a PR
  - an issue is moved from `needs:architect` back to `needs:implementer`
  - another agent reports that it cannot find review feedback
provenance: "Harvested from tiny-ipa M2 review cycle on 2026-06-07, where Implementer could see labels but not the reason for requested fixes until issue and PR comments were both used. Revised after Agent Foundry AF10-B to make human-gate live review points explicit."
---

## Principle

When review sends work back to an Implementer, put the handoff on both the PR and the child issue. Prefer review at a meaningful Epic, sub-Epic, or batch checkpoint instead of forcing review after every small child issue. An open child PR is not automatically an Architect review request.

## Rationale

Agents do not always enter work through the same surface. One may query issues by label; another may inspect PR comments. If detailed feedback exists only on the PR, the issue inbox lacks context. If the issue contains only a summary and the PR has no pointer, the Implementer may miss file-level review. Dual-surface handoff makes the routing signal and the actionable feedback meet.

Review itself is also a coordination cost. For small related issues inside one Epic, repeated per-issue review can turn the human or Architect into a message broker. When the work is low-risk and dependency-gated, let the Implementer complete the planned batch and review the combined evidence at the natural checkpoint. Child PRs remain useful traceability and integration units, but they are not by themselves blocking review gates.

Review is a validation state, not automatically a cross-session wait. In the lightweight scheduler model, a role can be fulfilled by the current session, the user, a separate Reviewer agent, CI/automation, or a batch/Epic checkpoint. The handoff must name the review target so the next action is detectable.

Human decision is a different state from agent review. When the next blocker is user judgment, authorization, or input, label the issue or PR `needs:human` and write a Human Decision Contract. The contract should explain what the user must understand and decide, not merely ask for a generic PR review.

If the user is waiting in the current conversation, also provide the human-gate review points in the live response: what boundary is being accepted, what was verified, what remains risky or subjective, what options are available, and what exact phrase or trial response unlocks the next action.

## Guidance

When Architect requests changes:

1. Post detailed code, API, or test feedback on the PR.
2. Post a short child-issue handoff comment that links to the PR feedback.
3. If the latest PR conversation does not already point to the handoff, post a short PR follow-up too.
4. Replace `needs:architect` with `needs:implementer` on the child issue.
5. Leave Project status as `In Review` unless the task is explicitly reopened.

When planning review granularity:

- Prefer Epic, sub-Epic, or batch review for related low-risk child issues.
- Before reviewing an individual child PR, check the issue's `Completion handoff`, the parent Epic queue, and whether a high-risk trigger is present.
- For any issue in `Review`, identify the review target: current Architect session structured self-review, user review, separate Reviewer agent, CI/automation, or batch/Epic checkpoint.
- If the same session switches from producing role to reviewing role, mark it as structured self-review and list residual risks. Do not present it as independent review.
- Require independent user or separate-agent review when the contract says so, the user requests it, or the work has high-risk privacy, security, irreversible architecture, external dependency, cost, or data-retention consequences.
- Review individual issues immediately when they introduce blockers, high-risk changes, unclear dependencies, privacy/security risk, schema/runtime boundary changes, external dependency/provider/cost changes, shared contract changes, or a failed verification signal.
- If the issue says `Completion handoff: batch checkpoint` and no high-risk trigger exists, do not create a blocking per-issue Architect review. Let the batch continue to its checkpoint.
- If a batch review sends work back, include both the batch-level summary and the specific issue or PR links that need action.
- Keep child issues traceable, but do not require a separate Architect interaction for every child issue when the review question is really batch-level.
- When an Implementer finishes evidence-only work, preliminary classification, or any task with Architect-owned decisions, the issue should move to `Review`, not `Done`. Remove `needs:implementer`, add `needs:architect` or `needs:reviewer`, keep the issue open, and post completion evidence plus residual risks.
- For a batch checkpoint, every completed child issue may move to `Review` while the Architect waits for the full batch before reviewing. Batch review reduces interactions; it does not mean child issues skip the review state.
- For high-risk reviews where self-review is not sufficient, include two explicit handoff artifacts:
  - Human review instructions: what the user should inspect or decide, the approval boundary, and the actions unlocked by approval.
  - Separate Reviewer prompt: copyable prompt text with issue, PR or commit, scope, required checks, output format, and prohibited actions.
- When a separate Reviewer agent is required, prefer dispatching to an existing Reviewer role thread if available. If live thread tools are not available, check for the runtime's subagent or multi-agent spawn capability before declaring dispatch impossible. Use a fresh subagent as a bounded fallback, not as the default replacement for an established role thread.
- Re-check the current session's exposed tool surface before deciding how to dispatch a separate Reviewer. In Codex, `list_threads`, `read_thread`, and `send_message_to_thread` can be present in one thread or launch mode and absent in another. If they are absent, report that current-session live thread tools are unavailable and explain the fallback; do not present that as proof the product feature was removed.
- If the reviewer prompt is sent from another live thread and a `source_thread_id` or caller thread identity is available, include it in the prompt. The Reviewer should post durable review evidence to the PR and issue first, then notify the source thread with the review decision, blocking findings, verification, residual risks, and next owner. If callback is unavailable, the Reviewer should say so in the durable handoff and leave enough issue/PR state for the source thread to detect completion later.
- When Architect and Reviewer have accepted a PR but final merge still requires explicit user authorization, move the PR and linked issue to `needs:human`, not `needs:architect`, and post the Human Decision Contract on both surfaces when practical.

For a human-gated issue or PR, the contract should include:

```markdown
## Human Decision Contract

Decision needed:
<one sentence naming the exact decision or input needed>

Why human is required:
<merge authorization, privacy/security/trust boundary, data migration, destructive action, cost/external dependency, product direction, or missing user-specific input>

Current agent conclusion:
<Architect/Reviewer/Implementer/Harvester result, including blocking findings or no-blocking-finding status>

Options:
1. Approve <specific action>
2. Request changes <what should change>
3. Defer <what remains blocked>

Consequences:
- If approved: <what the agent will do next>
- If changes requested: <where work routes next>
- If deferred: <which issue, PR, Epic, or stage remains waiting>

Verification already done:
<checks, reviewer comments, PRs, issues, commits, and residual risks>

Explicit authorization phrase:
<example phrase such as "批准 merge #85" or "批准 runtime apply">
```

The live response that asks for this decision should not collapse the contract to only the authorization phrase. It should carry the decision, review points, consequences, verification, residual risks, and phrase in compact form.

For a review-ready issue or PR, the handoff should include:

````markdown
## Review handoff

Review target: current Architect session structured self-review | user | separate Reviewer agent | CI/automation | batch/Epic checkpoint
Review surface: issue | PR | both
Producer role: Architect | Implementer | Reviewer | Harvester
Source thread callback: none | source_thread_id=<id> | caller thread=<name/id>
Residual risks: ...
Independent review required: yes/no, because ...
Human review instructions: ...
Separate reviewer prompt:
```text
...
```
Done condition: ...
````

The child issue handoff for requested changes should include:

```markdown
## Implementer handoff: changes requested

This issue was moved back to `needs:implementer` after Architect review.

Fix branch: `agent/<issue-number>-...`
PR: #...
Detailed review: <PR comment URL>

Next action:
- Checkout the fix branch.
- Apply the requested fix from the PR review comment.
- Add or adjust regression tests for the blocker.
- Push the same branch and move this issue back to `needs:architect` when ready for re-review.
```

## Use This When

- Review feedback crosses from Architect to Implementer.
- A batch of related issues is ready for Architect or Reviewer verification.
- Same GitHub account limitations prevent formal "request changes" review state.
- Labels moved but the next agent asks "what exactly needs fixing?"

## Watch Out For

- Do not rely only on labels. Labels route ownership; they do not carry enough context.
- Do not rely only on PR comments when agents discover work through issue labels.
- Do not ask the Implementer to create a replacement branch unless the existing fix branch is truly unusable.
- Do not create needless per-issue review churn when a batch checkpoint would catch the same risks with less handoff overhead.
- Do not treat an open child PR as sufficient reason to add `needs:architect`; review ownership follows the completion handoff, high-risk triggers, failed verification, or the batch/Epic checkpoint.
- Do not let an Implementer close an issue that still requires Architect-owned taxonomy, policy, privacy, security, harvest, generated-artifact, or Core/Vault decisions.
- Do not leave batch child issues in `Ready` after the producing agent has posted completion evidence; move them to `Review` until the batch is accepted.
- Do not equate `Review` with "wait for another session" unless the handoff names a separate reviewer. If the current session owns the review role, continue with structured self-review instead of stalling.
- Do not hide self-review behind generic review wording. Name the review mode so later agents and the user can judge independence.
- Do not make the user decide whether to review personally or spawn a Reviewer session without guidance; high-risk handoff must recommend the route and provide the reviewer-session prompt when needed.
- Do not claim that a separate Reviewer cannot be dispatched merely because one tool family is not exposed. Existing role-thread tools, subagent spawn tools, automations, and portable prompt fallback must be considered as separate options.
- Do not rely on old session evidence that thread tools were available or unavailable. The review handoff must be based on the current session's exposed tools.
- Do not use `needs:architect` as a parking lot for decisions that only the user can make. Once agent-side architecture and review are complete, route explicit human authorization or input through `needs:human`.
- Do not write Human Decision Contracts as vague "please review" messages. The user-facing contract must name the decision, options, consequences, verification, and exact approval phrase.
- Do not hide the review points inside GitHub when asking in chat for a human decision. The durable contract is authoritative, but the live request must still be intelligible on its own.
- Do not let callback replace dual-surface review. Notify the source thread only after the PR and issue contain the durable review state.

## Example

In tiny-ipa M2, issues were returned to `needs:implementer`, but DeepSeek initially could not find why. The fix was to add a durable issue handoff pointing to PR review details and ensure the PR conversation also contained the current handoff.

## Activation

- Tier: workflow_embedded
- Phases: review, handoff, re-review
- Signals: `needs:architect` to `needs:implementer`; PR review requested changes; agent cannot find feedback; same-account PR review limitation
- Evidence: report both the issue handoff URL and PR review/comment URL

## Related Practices

- [[COLLAB-002]]
- [[COLLAB-007]]
- [[COLLAB-008]]
- [[COLLAB-009]]

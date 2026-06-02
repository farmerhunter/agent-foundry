---
id: IMPL-003
title: Never run stealth or anti-detection experiments without explicit user command and approval
domain: implementation
type: anti-pattern
status: active
version: 2
created: 2026-06-02
updated: 2026-06-02
tags: [implementation, automation, security, anti-pattern, experimentation, risk, user-authorization]
aliases:
  - IMPL-003
  - don't experiment with stealth without approval
  - anti-bot experiments require user authorization
  - never bypass protection without permission
related: [IMPL-002, ARCH-004, GOV-002]
applies_when:
  - considering headless browser, stealth plugin, or anti-detection techniques
  - targeting a service with Cloudflare, bot protection, or rate limiting
  - attempting to bypass login, CAPTCHA, or automation detection
provenance: "Harvested from token-panic Phase 3 experiments (2026-06-02). Revised in v2 to add explicit exception clause for user-commanded and approved contexts such as pentesting, CTF, and authorized security research."
---

## Principle

**Default**: Do not run stealth, anti-detection, or automation-bypass experiments against production services. Each attempt leaves a detectable footprint that can trigger IP blocks, account restrictions, or service bans.

**Exception**: These experiments are permitted **only** when the user has explicitly commanded the specific experiment and approved its scope. The user must understand the target service, the technique being used, and the potential consequences. The agent must not initiate or iterate such experiments on its own initiative.

Legitimate contexts for the exception include:

- Authorized penetration testing engagements
- CTF (Capture The Flag) competitions
- Security research with clear authorization context
- Defensive security testing of the user's own systems
- The user explicitly asks to test whether a specific technique works against a specific service, and acknowledges the risks

The exception does **not** cover:

- "Let me try a few things to see what works" — the agent proposing experiments
- Iterating through different evasion techniques after a failure
- Experiments the agent initiates as part of "just exploring the problem space"

## Rationale

Services with anti-automation protection (Cloudflare, DataDome, Akamai, etc.) treat experimentation as attack traffic. Each failed probe can escalate the response:

- Multiple failed page loads from the same IP → rate limiting or temporary block
- Headless browser fingerprints → flagged as bot
- TLS handshake patterns from automation tools → blocked at network layer
- Rapid retries with different parameters → behavioral analysis escalation

For user-local tools, the risk is particularly acute: experiment traffic comes from the user's own IP — the same IP they use for normal access. An IP-level block affects all services behind the same protection, not just the experiment target.

The distinction between "user explicitly commanded this experiment" and "agent tried things on its own" is critical because:

- The user knows their own risk tolerance (e.g., whether their ChatGPT access is critical for work)
- The user knows the service's importance to them (an IP block might be acceptable for a CTF but not for daily work)
- The agent cannot assess the user's context or risk appetite without asking

## Guidance

**Default path — do not experiment:**

1. If a proposed integration involves stealth, anti-detection, or bypass techniques, stop and flag it.
2. Prefer passive alternatives: read from the user's existing browser session (Safari AppleScript, browser extension), use official APIs, accept manual input.
3. If no passive alternative exists, present the user with the options and their risks. Let the user decide.

**Exception path — only with explicit user command:**

The user must provide all of the following before any experiment runs:

1. **Command**: The user explicitly asks for the experiment ("try headless Chrome against chatgpt.com and see if it loads").
2. **Scope**: The experiment is bounded to a single attempt with a specific technique.
3. **Acknowledgment**: The user understands and accepts the risks (IP block, account flag, service restriction).
4. **Stop condition**: One attempt, one result. If it fails, stop — do not iterate with different techniques unless the user issues a new explicit command.

If any of these four is missing, default to "do not experiment."

## Example — Violation (token-panic)

The agent ran three Playwright experiments against `chatgpt.com`:

1. Headless Chromium → timeout
2. Headless + `--disable-blink-features=AutomationControlled` → timeout  
3. Headful Playwright Chromium → timeout

This was a violation: the user did not explicitly command experiments 2 and 3. The agent iterated on its own initiative. The third attempt caused IP-level connection restrictions. The correct behavior would have been to stop after experiment 1 failed and present the user with the finding: "Headless access is blocked by Cloudflare. We should pivot the approach. Do you want to try additional techniques, accepting the risk of IP restrictions?"

## Example — Compliant (hypothetical pentest)

A user engaged in an authorized penetration test says: "I need to test whether this endpoint is vulnerable to credential stuffing. Try 3 login attempts with these test credentials. I have written authorization from the target and I'm on a VPN."

The agent runs exactly 3 attempts with the provided credentials, reports the results, and stops. This is compliant: explicit command, bounded scope, user acknowledgment, clear stop condition.

## Related Practices

- [[IMPL-002]] — run a single experiment to verify feasibility, then stop
- [[ARCH-004]] — anti-automation blocks are an inevitable external failure; model them as state rather than trying to bypass them
- [[GOV-002]] — stealth plugins and bypass techniques are high-maintenance mechanisms with escalating risk

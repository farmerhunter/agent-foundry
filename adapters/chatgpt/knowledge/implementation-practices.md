# Implementation Practices

Canonical IDs: IMPL-001, IMPL-002, IMPL-003

## IMPL-001 Avoid Shell-Interpreted Markdown in CLI Comments

For GitHub comments containing Markdown with backticks, dollar signs, or command examples, use `--body-file` or another safely quoted path instead of shell-interpreted inline strings.

## IMPL-002 Verify External Behavior Before Committing to an Integration

Before writing code that depends on third-party behavior (APIs, web scraping, browser automation, file formats, protocols, SDKs), run a minimal disposable experiment to verify the external system actually behaves as assumed. The experiment is not part of the application — it is a throwaway probe that answers "can we even get the data?" before committing to "how do we structure the code?"

If the experiment fails: diagnose, record the finding, and decide whether to pivot the approach. Do not build integration code on an unverified premise.

## IMPL-003 Never Run Stealth/Anti-Detection Experiments Without User Approval

Default: do not run stealth, anti-detection, or automation-bypass experiments against production services. Each attempt leaves a detectable footprint that can trigger IP blocks, account restrictions, or service bans.

Exception: permitted only when the user explicitly commands the specific experiment and approves its scope. The user must understand the target, the technique, and the risks. The agent must not initiate or iterate such experiments on its own.

Legitimate exception contexts: authorized pentesting, CTF competitions, security research with clear authorization, defensive testing of the user's own systems.

If a probe fails due to anti-automation measures, stop. Do not iterate through evasion techniques without a new explicit user command.

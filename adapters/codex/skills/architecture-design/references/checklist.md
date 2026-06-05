# Architecture Design Checklist

Ask before proposing an architecture:

- What domain state does the user actually care about?
- Which concepts are stable and which are implementation details?
- Is the proposed architecture mostly a sequence of current tools or implementation steps?
- What remains stable if the current tool, API, storage, UI, workflow, or automation is replaced?
- Which dimensions can vary independently?
- Are we forcing different business meanings into one field or model?
- What external failures are inevitable?
- Should those failures be modeled as status?
- What summary should UI consume?
- Are UI actions, entry points, and card variants a cross-state contract that should be represented by a ViewModel instead of scattered JSX conditions?
- What is the MVP's main path?
- What design docs or user-facing runtime docs need to change so future agents understand the new boundary or flow?
- If a chosen technology is replaced, does the architecture still make sense?
- Before coding, has an implementation plan been written and reviewed to surface file-structure, boundary, contract, or protocol gaps?
- For fragile integrations, parser/capture/import flows, or local automation, what trace, stable failure reasons, metadata-only diagnostics, explicit debug artifact, and raw-data policy will let a future agent reproduce and fix failures? (DEBUG-001)
- For any integration depending on third-party behavior (API, scraping, browser automation, SDK): has a minimal disposable experiment verified that the external system actually behaves as assumed? (IMPL-002)
- If the integration involves stealth, anti-detection, or bypass techniques: has the user explicitly commanded and approved each specific experiment? (IMPL-003)
- For systems connecting independently-tested modules through glue code (adapter callbacks, IPC pushes, provider_id propagation): are the error paths tested through the full connecting pipeline, not just at the endpoints? (TEST-002)
- For packaged desktop/runtime artifacts, has the generated artifact been opened and smoke-tested in the target shell, including installer contents, icons, tray/menu behavior, startup, permissions, and quit path? (TEST-003)
- For background, tray, menu bar, daemon-like, or ambient apps, are install, open, settings, startup, identity, and explicit quit affordances discoverable from the product surface? (PROD-001)

---
id: TEST-003
title: Verify packaged runtime artifacts in the target shell
domain: testing
type: checklist
status: active
version: 1
created: 2026-06-04
updated: 2026-06-04
tags: [testing, packaging, runtime, smoke-test, desktop-apps, verification]
aliases:
  - TEST-003
  - verify packaged runtime artifacts
  - package success is not runtime success
  - test installers in the target shell
related: [TEST-001, TEST-002, ARCH-007, PROD-001]
applies_when:
  - packaging a desktop app, installer, DMG, tray app, menu bar app, browser extension, or other user-facing runtime artifact
  - command-line build or packaging succeeds but the artifact must work inside a host shell
  - the artifact includes icons, installers, context menus, file associations, permissions, startup entries, or OS-specific behavior
review_required: false
provenance: "Harvested from token-panic Phase 6B packaging QA on 2026-06-04, where successful Electron packaging still produced visible DMG support files, lost DMG file branding, and incorrect tray click behavior."
---

## Principle

Packaged artifacts must be verified inside the shell or host environment where users will run them. A successful build or package command only proves the artifact was produced, not that it behaves correctly at runtime.

## Rationale

Packaging often crosses out of ordinary application code and into OS or host-shell behavior: installers, mounted disk images, tray icons, file icons, context menus, startup items, permissions, and window placement. These behaviors can fail even when tests, type checks, builds, and packaging commands all pass.

The failure mode is especially common for desktop and packaged local tools. Generated support files can become visible in Finder, installer icons can disappear, tray context menus can bind to the wrong click event, or app windows can appear on an unexpected display. These are user-visible regressions that cannot be caught by unit tests alone.

## Guidance

After producing a packaged artifact, run a target-shell smoke test that exercises the real artifact:

1. Open or mount the packaged artifact in the intended host shell.
2. Inspect the user-visible contents, not just the generated file list.
3. Launch the app from the packaged output, not from development mode.
4. Exercise OS-level affordances: tray/menu bar left click, right click, quit, startup/login item, installer drag target, icon display, and permission prompts.
5. Use command-line structural checks as a supplement, not a substitute. For example, mount a DMG and inspect top-level files, but still visually verify Finder behavior when layout matters.
6. Record the smoke checklist in the implementation plan or release checklist so future packaging changes repeat the same verification path.

When a host-shell artifact has hidden support files, verify both default-user behavior and the behavior when hidden files are visible if the development environment often shows them.

## Use This When

- A build creates `.app`, `.dmg`, `.pkg`, `.exe`, `.msi`, browser extension package, mobile artifact, or other packaged runtime output.
- The artifact relies on OS shell behavior rather than only app code.
- A user reports "the package installed but looks wrong" or "the icon/menu/installer behaves strangely."
- An agent is about to declare packaging done after command success only.

## Watch Out For

- Do not treat `electron-builder`, `xcodebuild`, `vite build`, or similar command success as end-user verification.
- Do not rely only on file existence checks when the important behavior is visual or interactive.
- Do not skip packaging smoke tests because unit tests passed.
- Do not leave the smoke path implicit; future agents will otherwise repeat the same packaging mistakes.

## Example

In token-panic, `npm run package:mac` succeeded and produced a DMG. Opening the DMG revealed two visible support files, `.background.tiff` and `.VolumeIcon.icns`, because Finder was showing hidden files. A later fix removed those from the visible mounted contents, but then the DMG file itself lost its Finder icon. The final solution used a plain DMG background, disabled the volume icon support file, and applied a Finder custom icon to the DMG file after packaging.

The same packaging pass found that calling `tray.setContextMenu()` caused macOS to show the context menu on left click, conflicting with the intended left-click dashboard behavior. The fix was to open the dashboard on left click and manually call `tray.popUpContextMenu()` only on right click.

## Activation

- Tier: task_router
- Phases: packaging, release, verification, final_report
- Signals: package command success, installer generation, desktop app distribution, OS shell affordance, tray/menu bar app, mounted disk image, file icon, startup item, app bundle
- Evidence: final report names the packaged artifact opened, the target-shell smoke checks performed, and any OS-level behavior verified or intentionally deferred

## Related Practices

- [[TEST-001]]
- [[TEST-002]]
- [[ARCH-007]]
- [[PROD-001]]

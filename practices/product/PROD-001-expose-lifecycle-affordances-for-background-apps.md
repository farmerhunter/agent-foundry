---
id: PROD-001
title: Expose lifecycle affordances for background apps
domain: product
type: checklist
status: active
version: 1
created: 2026-06-04
updated: 2026-06-04
tags: [product, ux, desktop-apps, menu-bar, background-apps, lifecycle]
aliases:
  - PROD-001
  - background apps need lifecycle affordances
  - menu bar apps need quit and settings
  - ambient apps need explicit exit
related: [ARCH-007, TEST-003]
applies_when:
  - building a menu bar app, tray app, daemon-like utility, browser extension, background helper, or app without an obvious main window
  - the app can keep running after the primary panel or window is closed
  - users may need to install, configure, start on login, reveal status, or quit the app
review_required: false
provenance: "Harvested from token-panic Phase 6B usability QA on 2026-06-04, where the packaged menu bar app needed explicit install, settings, startup, and quit affordances."
---

## Principle

Ambient or background apps must expose their lifecycle controls directly in the product experience. Users should not need developer knowledge, Activity Monitor, terminal commands, or OS guesswork to install, configure, find, or quit the app.

## Rationale

Background tools are easy to make technically functional while remaining confusing to users. A normal app has a Dock icon, visible window, menu bar, and quit command. A menu bar or tray utility may have none of these cues. If the app lacks explicit lifecycle affordances, users can feel trapped: they can open it but do not know whether it is installed, where it runs, how to configure it, whether it starts on login, or how to exit.

This is a product contract, not just an implementation detail. The app's lifecycle must be discoverable where users already interact with it.

## Guidance

For background, menu bar, tray, or always-on utilities, define and verify these affordances before calling the shell done:

1. **Install**: show or document the expected install path, such as dragging an app into `/Applications`.
2. **Open**: provide the primary open/show action from the ambient surface.
3. **Configure**: provide a direct path to settings from the ambient surface.
4. **Startup**: expose whether the app starts on login when that behavior matters.
5. **Quit**: provide an explicit quit/exit action from the ambient surface.
6. **Identity**: provide enough app icon, tooltip, title, or label for users to recognize what is running.
7. **State collision**: when multiple lifecycle surfaces can be open at once, define which one wins. For example, right-clicking a tray icon may hide the dashboard before showing the context menu.

Use OS conventions. On macOS menu bar apps, a right-click context menu with settings and quit is often more discoverable than hiding those controls inside the transient panel.

## Use This When

- The app lives in the menu bar, system tray, background, extension toolbar, or notification area.
- Closing the visible panel does not actually quit the app.
- The app has startup/login behavior.
- The user asks "how do I install it?" or "how do I quit it?"
- The implementation has packaging but no explicit lifecycle UX.

## Watch Out For

- Do not assume users know platform-specific force quit or Activity Monitor workflows.
- Do not confuse panel close/hide with app quit.
- Do not bury quit or settings behind a state that may itself fail to open.
- Do not reuse a tiny tray glyph as the only app identity if larger shell surfaces need a clearer icon.
- Do not make lifecycle behavior depend on dev-mode commands once the app is packaged.

## Example

In token-panic, the first packaged menu bar app could open a dashboard, but users had no obvious quit path and no clear install story. Phase 6B added a DMG Applications link, a login item toggle in Settings, a clearer app icon for Finder/DMG, and a tray right-click menu with Open, Settings, Startup, and Quit. The right-click menu also hides the dashboard before opening so the transient panel and lifecycle menu do not overlap.

## Activation

- Tier: task_router
- Phases: packaging, product_review, usability_review, release
- Signals: menu bar app, tray app, background process, daemon utility, no visible main window, app starts on login, user asks how to quit or install
- Evidence: final report lists the lifecycle affordances implemented or explicitly deferred

## Related Practices

- [[ARCH-007]]
- [[TEST-003]]

<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones notes for phosphor-works:cpp-qt-reviewer

PlasmaZones is a Wayland-only window tiling app for Plasma (Qt6, KF6, C++20). Apply these notes in addition to the shared reviewer's checks.

## Scope and hand-offs in PlasmaZones
- The C++ core reviewer covers `plasmazones/src/core`, `plasmazones/src/daemon`, `plasmazones/src/dbus`, `plasmazones/src/common`, `plasmazones/src/shared`, and the C++ of `../phosphor-libs/libs/phosphor-*` and `../phosphor-engine-libs/libs/phosphor-*` not claimed by another specialist, including `../phosphor-libs/libs/phosphor-protocol` (the D-Bus contract library).
- Hand-offs: Wayland wrappers, the QPA plugin and layer-shell code go to `phosphor-works:wayland-reviewer`. Rendering and compositor libs, phosphor-surface-quick and the shaderpreview, shadervalidate and tools hosts go to `plasmazones:kwin-compositor-reviewer`. phosphor-config and phosphor-shortcuts go to `phosphor-works:config-reviewer`. phosphor-tiles and the phosphor-scripting Luau glue go to `phosphor-works:luau-reviewer`.
- Licensing: `plasmazones/src/**` is GPL-3.0-or-later. `../phosphor-libs/libs/phosphor-*/**` and `../phosphor-engine-libs/libs/phosphor-*/**`, including their own `tests/`, are LGPL-2.1-or-later.

## PlasmaZones invariants
- Zone identity is always by QUuid, never index.
- Architecture: the in-partition exemplar of service-oriented constructor DI is `WindowTrackingService` in phosphor-placement. The editor-side `ILayoutService`, `ZoneManager` and `SnappingService` live in `plasmazones/src/editor`, which routes to `phosphor-works:qml-reviewer`.
- JSON persistence uses relative geometry 0.0–1.0.

## Known past-bug shapes to check for (from prior audits)
- Per-(screen,desktop,activity) state keyed wrongly: desktop is per-window data, never the store key; single-owner guards (home: `WindowTrackingService::snapForWindow` in phosphor-placement) prevent a window appearing in two SnapStates.
- **Correct exactly once.** The KWin effect re-drives D-Bus operations it observes as not having taken (the unminimize unfloat retries three times at 250 ms; drag and mode-swap paths re-assert). A daemon-side write that consumes a one-shot flag is right on call 1 and wrong on call 2.
- **Mode-lens vs. caller-screen asymmetry.** `WindowTrackingService::isWindowFloating` and friends answer through the mode of the window's TRACKED screen, while `*ForScreen` writers route by the CALLER's live screen. Using the facade to check the result of a routed call is a real defect; ask the routed engine instead.
- **State-carrying migrations.** `SnapState::migrateWindowTo` carries the zone assignment verbatim while rewriting the live screen. Anything that migrates before a capture changes what the capture records. (A reviewer once proposed a re-home before a capture as the fix, unread. The capture then recorded monitor A's zone paired with monitor B.)
- **Unknown collapsed into a default.** The minimize-preserve capture and the seed deferral both failed open this way. Where unknown must be treated conservatively, read `WindowRegistry::minimizedState()` rather than `isMinimized()`.
- **Empty input read as "everything is gone".** `WindowRegistry::pruneStaleInstances` and the adaptor's `pruneStaleWindows` once took an empty alive set (a login-time one-shot report) as all-dead and wiped the registry and persisted assignments.
- **Bulk operations scoped wider than their trigger.** A per-screen toggle pre-clearing every screen's saved orders, `buildAutotileRestoreEntries` with no screen filter teleporting windows still tiled elsewhere, a master-switch round trip replacing `m_lastAutotileOrders` wholesale or stripping activity-scoped assignments, an unplug stripping `allowedScreens` for good.
- **`stop()` then `init()` is a real path.** Re-init after `Daemon::stop()` leaked second adaptors holding stale engine pointers, stacked duplicate `rulesChanged` connections, and kept per-run state (`m_lastTiledCountByScreen`, `m_pendingSnapFloatRestores`). For each member or connection a change adds in `daemon/init_*.cpp`, find its clear on the stop path in `daemon/lifecycle.cpp`.
- **A gate on one method of a bus surface, not its siblings.** `admitCompositorReport`, `admitBusSnap`/`admitBusFloat` and `trustIfCompositor` were added to one call while siblings reaching the same state stayed open (`windowSnappedMultiZone`/`windowUnsnapped`, `resolveWindowRestore`, the batched-resnap restore arm, first-come `registerBridge`).
- **Re-entrant emits during iteration or write-back.** `WindowRegistry::remove` clobbering a re-canonicalized mapping, `clear()` replaying pending upserts, `refreshOpenWindowPlacements` walking a map its callees mutate.
- **Generation counters and compute barriers.** In `LayoutComputeService` a generation bump hoisted above the cached early return superseded an in-flight worker, a fast path dropped the layout's dirty term (`Layout::needsRecalc()`), and a stale worker result cleared the dirty flag; barriers keyed on screen alone drained early or hung when a screen left mid-flight.

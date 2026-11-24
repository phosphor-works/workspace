<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones notes for phosphor-works:wayland-reviewer

PlasmaZones is Wayland-only KDE tiling with a custom layer-shell QPA plugin for its overlays. Apply these notes in addition to the shared reviewer's checks.

## Scope and hand-offs in PlasmaZones
- The Wayland reviewer covers `../phosphor-libs/libs/phosphor-wayland`, `../phosphor-libs/libs/phosphor-layer` and any PlasmaZones code speaking raw Wayland or Qt Wayland client internals.
- `../phosphor-libs/libs/phosphor-protocol` is the D-Bus contract library and goes to `phosphor-works:cpp-qt-reviewer`.

## PlasmaZones invariants
- Exclusive zones interact with `mayReserveScreenEdge` on the KWin effect side. A panel that reserves an edge must keep the daemon's available-geometry sensor consistent (this desynced before).
- PerScreen placement is known-broken for layer panels. Do not assume per-output surface mapping is sound without reading it.
- `PLASMAZONES_EXPORT` appears in zero files outside `plasmazones/src/**`, so writing it into a phosphor library header names an undefined macro and breaks the build.

## Known past-bug shapes to check for (from prior audits)
- The shared reviewer carries the session-lock, user-data sever, unacked-configure exposure, shell-role and warm-surface shapes, because they live in phosphor-wayland and phosphor-layer. A passive PlasmaZones overlay surface was the one that stayed mapped above every window with effects off.

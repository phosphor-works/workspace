---
id: fractional-scale-hides-one-pixel-defects
title: Fractional scale hides one-pixel defects
repos: [all]
domains: [cpp-qt, wayland, geometry]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`QRectF::toRect()` and `qRound(logical * scale)` move an edge by a pixel at 1.15 or 1.25. That broke exact rect
compares in PlasmaZones' scroll engine, snap engine and editor. Check rect compares and scale-derived sizes at a
fractional scale (PlasmaZones' nested harness runs at 1.25).

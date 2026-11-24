---
id: the-first-apps-phosphor-libs-pin-wins
title: In a tree with several projects, the first app's phosphor-libs pin wins
repos: [phosphor-engine-libs, phosphor-shell-libs, phosphor-components, PlasmaZones, Lambent]
domains: [build, cmake]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

When an app adds phosphor-engine-libs, phosphor-shell-libs or phosphor-components, the app's own phosphor-libs pin
is already in the tree, so the library's pin is never used. Drift between the two pins stays hidden until the
library builds on its own. Keep the pins equal, or test the library alone after a bump.

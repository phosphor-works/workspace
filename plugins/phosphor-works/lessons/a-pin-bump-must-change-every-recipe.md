---
id: a-pin-bump-must-change-every-recipe
title: A branding or surface-packs pin bump must change every app recipe too
repos: [PlasmaZones, Lambent, branding, phosphor-surface-packs]
domains: [build, packaging]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

An app repeats each pin outside CMake. A bump of branding or phosphor-surface-packs changes
`cmake/<App>Dependencies.cmake` and the app's packaging: PlasmaZones' `packaging/nix/package.nix`, `arch/PKGBUILD`,
`rpm/plasmazones.spec` (and `debian/copyright` for branding), and Lambent's `packaging/nix/package.nix`.
PlasmaZones' dep-pins conventions rule names a recipe that misses the new pin.

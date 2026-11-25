---
id: lambent-surface-packs-pin-predates-breaking-changes
title: Lambent's surface-packs pin is older than two breaking commits
repos: [Lambent, phosphor-surface-packs]
domains: [build, shader]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Lambent pins phosphor-surface-packs at `087bd74`, before the two `refactor!:` commits that dropped
`uSurfaceOpacity` and the compatibility overloads. Its next pin bump needs the matching change in Lambent's surface
code in the same pull request.

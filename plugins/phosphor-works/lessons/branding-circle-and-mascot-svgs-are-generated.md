---
id: branding-circle-and-mascot-svgs-are-generated
title: branding's circle and mascot SVGs are generated
repos: [branding]
domains: [branding]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`svg/circle/` comes from `svg/square/` through `scripts/variants.py`, and `svg/mascot/` comes from
`scripts/mascots.py`. Edit the square icon or the script and run it. An edit to a generated SVG is lost, and
`check.py` fails on a stale circle variant.

---
id: the-website-config-needs-the-sibling-checkouts
title: The website's Astro config needs the sibling checkouts
repos: [website]
domains: [build, ci]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`astro.config.mjs` reads Afterglow's docs and the gallery sources through `scripts/upstream-checkouts.mjs`, so
`astro check` and `astro build` stop at loading the config when the siblings are missing. A local build works
beside the other clones, but CI must clone them first (`PHOSPHOR_WORKS_SRC`).

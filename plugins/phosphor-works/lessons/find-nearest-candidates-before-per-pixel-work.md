---
id: find-nearest-candidates-before-per-pixel-work
title: Find the nearest candidates before per-pixel work
repos: [Afterglow]
domains: [shader, perf]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Per-pixel loops over every card cost 10 ms at 4K with 27 panes. Find the nearest candidates first, then shade only
those. Measure with `afterglow_renderpng --timings --pixels 3840x2160`.

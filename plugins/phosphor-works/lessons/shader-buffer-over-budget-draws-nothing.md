---
id: shader-buffer-over-budget-draws-nothing
title: A persistent shader buffer over the budget draws nothing
repos: [Afterglow]
domains: [shader]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

A persistent shader buffer over the 256 MiB budget was transparent with no message, so the Orrery pack drew
nothing. Now it renders smaller and logs a warning. When a pack draws nothing, check the budget log first.

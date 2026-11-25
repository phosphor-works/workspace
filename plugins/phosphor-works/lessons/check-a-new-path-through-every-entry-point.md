---
id: check-a-new-path-through-every-entry-point
title: Check a new code path through every entry point
repos: [all]
domains: [test, design]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Afterglow's `newTab` did not start the tab transition, because the code read `m_splits` before the tab had one.
Check a new path through every entry point (keys, menu, script, the control CLI), not only the one you tested.

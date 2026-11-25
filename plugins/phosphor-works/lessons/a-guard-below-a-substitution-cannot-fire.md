---
id: a-guard-below-a-substitution-cannot-fire
title: A guard below a substitution cannot fire
repos: [all]
domains: [cpp-qt, design]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

If a caller already swapped in a plausible fallback, the callee cannot tell that the value is not real. Put the
guard where the information still exists, check what every caller actually passes, and delete a guard that cannot
fire.

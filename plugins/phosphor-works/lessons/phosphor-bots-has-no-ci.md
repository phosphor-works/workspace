---
id: phosphor-bots-has-no-ci
title: phosphor-bots has no CI, so only a local build checks it
repos: [phosphor-bots]
domains: [ci, build]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

No workflow builds phosphor-bots. A build with GCC alone hides Clang warnings, and the FreeBSD target is checked
only by hand. Build with both compilers before a pull request.

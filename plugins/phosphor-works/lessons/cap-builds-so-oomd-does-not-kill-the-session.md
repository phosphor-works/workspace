---
id: cap-builds-so-oomd-does-not-kill-the-session
title: Cap heavy builds and tests, or systemd-oomd kills the user's session
repos: [all]
domains: [build, test]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

A session can run in the cgroup of the user's terminal. When builds and tests filled memory and swap, systemd-oomd
killed that whole unit four times, and every Afterglow window of the user closed. Run heavy builds and tests in
`systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0`, with no more than one build at a time.

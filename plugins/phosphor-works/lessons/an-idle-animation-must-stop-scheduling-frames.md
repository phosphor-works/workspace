---
id: an-idle-animation-must-stop-scheduling-frames
title: An animation must stop scheduling frames when nothing moves
repos: [all]
domains: [animation, perf]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

An effect that animates only while visible must still stop scheduling frames when it has nothing to move.
Afterglow's pane effects kept the window at full frame rate while a pane was remote, until `active` and `moving`
became separate states.

---
id: wait-for-a-menu-to-settle-before-input
title: A test that clicks or types right after a menu loads must wait for its layout and its deferred focus
repos: [all]
domains: [test, qml]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

phosphor-shell-libs' tray test failed now and then on CI and on one CPU locally, and a longer tryVerify timeout did
not help: the misses were races, not slowness. Rows placed by a ColumnLayout move only when the window draws a frame,
so a click right after the rows exist lands where a row was (the panel was 175 of its 345 px). And TrayMenu moves
focus to its first row from a zero-interval Timer after it loads, which on a loaded runner fires after the test has
moved focus, so the next key acts on the wrong row. Wait for the component's own ready state (here `pendingFocus`
false) and draw a frame (`waitForRendering`) before input. Reproduce such a failure with `taskset -c 0 ctest
--repeat until-fail:40` before you call it fixed.

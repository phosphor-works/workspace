---
id: ci-runs-as-root-without-usr
title: CI runs tests as root, and the Nix sandbox has no /usr
repos: [all]
domains: [test, ci, nix]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

CI runs the suite as root in an Arch container and in the Nix build sandbox, where only `/bin/sh` (BusyBox ash) has
a fixed path and `/usr` does not exist. 59 Afterglow tests failed there on `/bin/cat`, `PATH=/usr/bin:/bin`, a `$`
prompt that no PS1 set, and `/usr` as a directory. A test finds a program through `PATH`
(`QStandardPaths::findExecutable`, or a helper such as Afterglow's `MuxTest::programInPath`), and sets the PS1 that
it waits for. A copy of a Phosphor header in `/usr/include` also hid a library that a target did not link: only CI
saw it.

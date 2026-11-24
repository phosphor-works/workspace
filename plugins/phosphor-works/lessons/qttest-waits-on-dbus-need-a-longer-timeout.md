---
id: qttest-waits-on-dbus-need-a-longer-timeout
title: QtTest's 5 s default is too short for a wait that crosses D-Bus on CI
repos: [all]
domains: [test, qml, ci]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

phosphor-shell-libs' tray test failed on the Nix aarch64 runner: a `tryVerify` gave up after 5 s while the Python
D-Bus fixture was still answering, and main passed there. A test file whose waits cross D-Bus to a fixture gives
them one longer timeout (`readonly property int busTimeout: 20000`, passed to every `tryVerify` and `tryCompare`).
A wait that succeeds still returns at once.

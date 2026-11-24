---
id: a-missing-test-isolation-module-runs-silently
title: A test tree that cannot find PhosphorTestIsolation runs without isolation
repos: [phosphor-libs, phosphor-engine-libs, phosphor-shell-libs, phosphor-components, PlasmaZones]
domains: [test, cmake]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

The library test trees include `PhosphorTestIsolation.cmake` behind an EXISTS guard (a relative `../../../cmake/`
path in phosphor-libs, `PHOSPHOR_LIBS_CMAKE_DIR` elsewhere) and fall back to a stand-in that skips the private
D-Bus and the XDG sandbox. A wrong path keeps CI green while the tests reach the real session bus and the user's
config. Count the directory levels against the caller when you move a test tree.

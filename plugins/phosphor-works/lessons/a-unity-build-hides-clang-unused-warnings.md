---
id: a-unity-build-hides-clang-unused-warnings
title: A unity build hides Clang's unused-variable warnings and relative __FILE__ paths
repos: [all]
domains: [build, ci]
added: 2026-11-25
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Clang reports an unused constant, variable or function only in the main file of a compile. A unity build includes
each source into a generated file, so no source is a main file, and these warnings stay hidden. The phosphor-libs
Clang job passed with an unused constant in a test, and the Clang jobs of Lambent and phosphor-components, which
build those tests without unity, failed on it. phosphor-engine-libs had a second one. The shared Clang job now
configures with `-DCMAKE_UNITY_BUILD=OFF`. To find these warnings locally, build with Clang and that option, not
with the dev preset alone.

A unity build also changes `__FILE__`. The unity source includes each file by its absolute path, so `__FILE__`
is absolute. Without unity, Ninja passes a path relative to the build directory. PlasmaZones'
`test_compositor_only_gate` found its data from the directory of `__FILE__`, passed in the unity GCC jobs and
failed in the Clang job. Give a test its source paths as compile definitions from CMake, never from `__FILE__`.

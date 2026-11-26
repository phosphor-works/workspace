---
id: a-unity-build-hides-clang-unused-warnings
title: A unity build hides Clang's unused-variable warnings
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

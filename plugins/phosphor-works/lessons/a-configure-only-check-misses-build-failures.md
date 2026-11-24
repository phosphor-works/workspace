---
id: a-configure-only-check-misses-build-failures
title: A configure-only check misses build failures
repos: [all]
domains: [build, verification]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

The first workspace superbuild configured cleanly with the expected 784 tests, but the build then failed twice: a
unity build leaked into Afterglow's zlib-ng, and one shared test PCH did not match the apps' flags. A configure
proves only that CMake accepts the tree. Build and run the tests before you call a build change done.

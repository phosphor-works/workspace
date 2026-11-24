---
id: absence-is-evidence-only-if-the-instrument-ran
title: An absence is evidence only if the instrument ran
repos: [all]
domains: [build, test, verification]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

A zero grep count, a build with no errors and a suite with no failures look the same when the target, binary or
test did not exist (a mistyped `--target`, a stale binary, a `BUILD_TESTING=OFF` build directory). Check the exit
code and that the thing you measured exists before you trust a clean result.

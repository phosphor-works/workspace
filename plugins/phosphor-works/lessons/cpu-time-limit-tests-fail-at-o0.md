---
id: cpu-time-limit-tests-fail-at-o0
title: Tests of CPU-time limits fail in a -O0 build on a slow machine
repos: [all]
domains: [test, luau]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Afterglow's script tests hold handlers to a 20 ms CPU-time limit with a loop that takes about 3 ms optimized. At
Debug `-O0` on a GitHub runner the loop passed the limit, and three tests failed that pass on a desktop and in
every optimized CI. The vendored Luau now builds `-O2` in Debug, and the workspace CI builds `relwithdebinfo`. A
test that depends on a time margin must leave room for an unoptimized build, or set its own limit.

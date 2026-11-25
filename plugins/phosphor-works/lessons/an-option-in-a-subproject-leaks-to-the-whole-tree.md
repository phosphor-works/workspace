---
id: an-option-in-a-subproject-leaks-to-the-whole-tree
title: An option() or CACHE variable in a subproject reaches the whole tree
repos: [all]
domains: [build, cmake]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`option(CMAKE_UNITY_BUILD ... ON)` in PlasmaZones put the setting in the cache, so in the workspace superbuild
every later project and its third-party code built as unity, and Afterglow's zlib-ng failed. A setting that belongs
to one project is a directory variable when the project is not top-level (`PROJECT_IS_TOP_LEVEL`). The same holds
for helpers that walk the tree from `CMAKE_SOURCE_DIR` and for fixed target names.

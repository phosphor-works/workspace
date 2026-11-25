<!-- SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team -->
<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->

<!-- BEGIN shared: tools/sync writes this block from workspace/sync/claude-header.md. Change it there. -->
<!-- END shared -->

## Overview

@DESCRIPTION@ It is a library repository of phosphor-works and builds on phosphor-libs.

## Layout

- Each library is `libs/<name>/` with its own `CMakeLists.txt`, `project()`, `include/`, `src/`, `tests/` and
  find_package config, so it also configures alone. The root `CMakeLists.txt` adds them in dependency order.
- Headers are `<PhosphorX/...>`, the target `PhosphorX::PhosphorX`, the export macro `PHOSPHORX_EXPORT` (from
  `generate_export_header`) and the namespace `PhosphorX`. The first library is `libs/@LIB@` (`@LIBTARGET@`).

## Build and test

- `cmake --workflow --preset dev` configures into `build/`, builds phosphor-libs and every library here, and tests.
  Follow `phosphor-works:build` for the memory cap, jobs and warnings.
- CI is the shared C++ CI of the workspace repository (`cpp-ci.yml`): the `dev` preset on Arch, with a warning
  failing the build, and clang-format and qmlformat on every tracked file. There is no flake yet, so the Nix jobs are
  off. Add `flake.nix` and `nix/package.nix` and drop `nix: false` from `ci.yml` to turn them on.
- `cmake/@PROJECT@Dependencies.cmake` pins the phosphor-libs commit (VERSION, URL, FILE and SHA256, changed together)
  and CPM.cmake. `-DCPM_phosphor-libs_SOURCE=<dir>` builds against a local checkout.

## Rules

- Everything here is `LGPL-2.1-or-later`, the tests included.

## Other repositories

- An app that uses a library here pins one commit of this repository and adds it with CPM, as PlasmaZones does with
  phosphor-engine-libs. After a change here merges, move that app's pin.

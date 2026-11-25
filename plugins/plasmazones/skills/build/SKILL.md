---
name: build
description: "Configure, build and test PlasmaZones correctly: its build dirs, tools, shader gates, test launcher, non-unity tree and conventions gate, on top of phosphor-works:build. Use when: build, rebuild, run the tests, run ctest, verify it compiles, is it green, check the build, before committing."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# PZ Build & Test

Follow `phosphor-works:build` first: presets, the memory cap, `BUILD_TESTING`, the warning check,
`--no-tests=error`, the non-unity and PCH gates, and why subagents never build. This skill adds what is
PlasmaZones' own.

## Build dirs that already exist

| dir | testing | unity | use for |
|---|---|---|---|
| `build` | ON | ON | day-to-day work |
| `build-release` | ON | ON | the release preset, optimized |
| `build-nounity` | ON | OFF | packager parity and the clangd compile database |
| `build-make` | ON | ON | Unix Makefiles generator parity; tools OFF, so a green ctest here does not cover the tools |

`build` is what `cmake --preset dev` produces, and `CMakePresets.json` sets
`BUILD_TESTING` and `BUILD_TOOLS` both ON there. `build-asan` (the `asan`
preset) adds ASan and UBSan. Add `BUILD_TOOLS` to the `grep` of the shared skill.

## Configure

- `BUILD_TOOLS=ON` adds `shader-render` and friends.
- The `shader_validate_animations`, `shader_validate_surface` and
  `shader_validate_pointer` gates shell out to `glslangValidator` (or `glslang`)
  and **hard-fail when neither is on PATH** rather than skipping. On x86-64 the
  configure fetches the glslang release `cmake/PlasmaZonesDependencies.cmake`
  pins and puts it on those tests' PATH, so only another architecture needs the
  distro glslang package.
- The first configure of a fresh tree downloads into `.cache/cpm`:
  phosphor-libs and the Luau and jsoncons it pins, the other pins of
  `cmake/PlasmaZonesDependencies.cmake`, and glslang. Offline, fill the archive
  dir with `cmake -DPHOSPHOR_DEPS_FETCH=<dir> -P cmake/PlasmaZonesDependencies.cmake`.

## Test

The test presets ask for 6 jobs. Pass `-j3` to `ctest`.

The isolation sweep of the shared skill is at the bottom of
`plasmazones/tests/unit/CMakeLists.txt`. New tests go ABOVE it. A test
registered below that line gets no launcher and no XDG sandbox, and the
installed `plasmazonesd` can get activated on the test's bus.

Never `pkill -f plasmazonesd`; that kills the user's real desktop daemon. Kill
only `build/bin/` test binaries.

## Non-unity

After touching daemon, engine or effect sources, build `build-nounity`, with
`-DENABLE_PCH=OFF` as well when a change touches tests.

`build-nounity` is a Ninja tree; `build-make` is the only Unix Makefiles one,
and that generator rejects ninja's `-k 0`.

## Conventions gate

```bash
python3 scripts/check-conventions.py
```

Stdlib only. A whole-tree run is around 13 seconds on an idle machine, and
noticeably longer while a build is running, so measure it idle before
concluding it is slow. A staged subset is near instant, which is the form
pre-commit uses (`--staged`). CI runs it whole-tree. See `--list-rules`.

## Green does not mean it works

The engine invariants that matter have historically been caught by live
verification and by invariant checks, not by the unit suite. For anything
touching placement, use the `plasmazones:verify-live` skill before claiming a
fix works.

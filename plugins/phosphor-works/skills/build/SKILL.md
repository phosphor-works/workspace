---
name: build
description: "Configure, build and test any phosphor-works repository (an app, a library or the workspace superbuild) and decide when a build is green. Covers the presets, the memory cap, the configure flags that make a suite silently run nothing, the warning check that replaces the exit code, the non-unity and shared-PCH gates, and the pinned dependencies. Use when: build, rebuild, run the tests, run ctest, does it compile, is it green, check the build, before committing."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Build and test a phosphor-works repository

Run every command from the repository root. When the repository has an app build skill (`plasmazones:build`,
`afterglow:build`), follow this skill first, then that one. Lambent and the libraries need only this skill and their
`CLAUDE.md`.

`BUILD_TESTING` defaults to `OFF` in every repository and **fails as success**. A build dir configured without it
produces no tests at all, and plain `ctest` then prints "No tests were found" and exits 0, which reads like a pass.
Most of what follows exists because that failure mode is invisible.

## Presets

Use a preset. A preset turns on `BUILD_TESTING` and picks the generator (Ninja) and the build dir.

| Repository | Configure presets | Build dir | Notes |
| --- | --- | --- | --- |
| Every C++ repository: PlasmaZones, Afterglow, Lambent, phosphor-libs, phosphor-engine-libs, phosphor-shell-libs, phosphor-components, phosphor-bots | `dev` (Debug), `release`, `relwithdebinfo`, `asan` (ASan and UBSan at `-O1`) | `build`, else `build-<preset>` | One shared file that `workspace/tools/sync` writes. Each preset has a build, test and workflow preset: `cmake --workflow --preset dev` configures, builds and tests. The test presets set `noTestsAction` to `error`. PlasmaZones also turns on `BUILD_TOOLS`, Afterglow `AFTERGLOW_BUILD_TOOLS`. |
| `workspace` superbuild | `dev` (Debug), `release`, `relwithdebinfo`, `asan`, and one app alone: `plasmazones`, `lambent`, `afterglow`, each with an `-asan` twin | `build`, else `build-<preset>` | Builds every library from its sibling checkout. Builds and tests run 3 jobs. |

Read the repository's `CMakePresets.json` when you need more: presets change, and this table can fall behind.

The superbuild is for a change that spans a library and an app. It builds each library from the sibling checkout
in place of the commit the app pins (it sets `CPM_<library>_SOURCE`), and CPM prints one expected "version
overridden" warning per library. An app's own presets build the pinned commits, as its CI and packages do. A
failure in the superbuild that an app's CI does not show usually means that app's pin is behind a library's `main`.

## Check what a build dir is

Check what a dir actually is before you trust a green result from it:

```bash
grep -E "^(BUILD_TESTING|CMAKE_BUILD_TYPE|CMAKE_UNITY_BUILD|ENABLE_PCH|CMAKE_GENERATOR):" build*/CMakeCache.txt
```

A dir configured by hand without `-DBUILD_TESTING=ON` is the one that runs nothing. Reconfigure it with the preset,
or pass `-DBUILD_TESTING=ON`.

## The memory cap and one build at a time

The machine has 16 GB. Without a cap, systemd-oomd stops the whole unit the session runs in, which can be the
user's desktop session or the user's terminal with all its windows. Inside a scope, the kernel stops only the build
at the cap.

- Run every build and every test run in the capped scope:
  `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 <command>`.
- Run one build or test run at a time, in the whole machine. Never start a second one beside it.
- Use 3 jobs. Only the `workspace` presets set it. For any other preset, set `CMAKE_BUILD_PARALLEL_LEVEL=3` and
  `CTEST_PARALLEL_LEVEL=3`, or pass `-j3`. A higher guess, or `$(nproc)`, has overloaded the machine before.
  PlasmaZones' test presets ask for 6 jobs: pass `-j3` to `ctest`.
- Count the jobs that a build starts beside the main one (an `ExternalProject` or a codec build) in the cap.

## Build

```bash
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 \
    env CMAKE_BUILD_PARALLEL_LEVEL=3 cmake --build --preset dev 2>&1 | tee <scratchpad>/build.log | tail -5
grep -c "warning:" <scratchpad>/build.log
grep -c "error:" <scratchpad>/build.log
```

`<scratchpad>` is the session scratchpad directory. Never write logs into the repository or into `/tmp`.

To see every file that does not compile in one run, keep going past the first error with
`cmake --build --preset dev -- -k 0`, as the libraries' CI does. Only Ninja takes `-k 0`. The Unix Makefiles
generator rejects it.

## The build is not green just because it has no errors

The repositories build with `-Wall -Wextra` (KDECompilerSettings, and `-Wpedantic` in Afterglow) and **not**
`-Werror`. The exit code and an error-only grep sail straight past warnings, and the user treats a warning as a
defect.

- Zero warnings is the bar. Check the count of `warning:` in the log, not the pipeline's exit status: `grep -c`
  exits 1 on zero matches.
- An incremental build only re-surfaces warnings for the files it recompiled. After a batch of edits, `touch` the
  changed files and rebuild before you claim the build is warning-clean.
- Known trap: a trailing member added to a brace-initialized aggregate needs a `= {}` default member initializer,
  or every site that omits the initializer warns.

## Test

```bash
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 \
    ctest --test-dir build --output-on-failure --no-tests=error -j3 2>&1 | tail -15
```

- `--no-tests=error` turns "No tests were found" into a failure. Always pass it, also with `-R PATTERN`: a pattern
  that matches nothing is the same silent pass.
- Use `-R PATTERN` while you work, and run the whole suite before a commit.
- The libraries' and Lambent's CI run `ctest` with `QT_QPA_PLATFORM=offscreen`. A test that passes locally and
  fails in CI can need a display that CI does not have.

### Test isolation

The phosphor-libs CMake helper `PhosphorTestIsolation.cmake` gives each test a private D-Bus and a private XDG
tree. The trees reach it through `PHOSPHOR_LIBS_CMAKE_DIR`. Each test tree calls
`phosphor_apply_directory_test_isolation()` at the bottom of its tests `CMakeLists.txt`.

- The test launcher is `dbus-run-session` with `test-session-bus.conf`. That conf declares **no** service dirs on
  purpose. A stock `dbus-run-session` still reads the standard service dirs, so an installed daemon gets activated
  on the private bus, holds the test's stdout pipe open, and **ctest hangs after the test passes**.
- Without the XDG half, a test that resolves a config or data path writes into the user's real `~/.config` and
  `~/.local/share`.
- Add a new test ABOVE the sweep, so the sweep picks it up. A test registered below that line gets no launcher and
  no XDG sandbox.
- A library test tree that walks up to the module with a relative path (`../../../cmake/`) falls back to a stand-in
  that silently un-isolates when the path is wrong, and CI stays green. Count the levels against the caller.

## Non-unity is a separate gate

Every repository but Afterglow builds as unity by default (`CMAKE_UNITY_BUILD`, or `PLASMAZONES_UNITY_BUILD` and
`LAMBENT_UNITY_BUILD` inside a superbuild). A unity blob pulls a symbol in from whichever sibling file happens to
include it. A file can therefore call something it never included and stay green, and only a packager's non-unity
build fails. The worst shape is not a missing include but a real cross-file dependency on a function with internal
linkage (a `static` or a function in an anonymous namespace), which links only under unity.

Test sources have a second hole of the same kind. Every test target reuses one shared precompiled header
(`PhosphorTestPch.cmake` in phosphor-libs, through `phosphor_share_test_pch()`, switched by `ENABLE_PCH`), so a
test can use a QtCore or standard header that it never included.

After a change to library, engine or app sources, or to tests, build a non-unity tree without the PCH:

```bash
cmake --preset <debug-preset> -B build-nounity -DCMAKE_UNITY_BUILD=OFF -DENABLE_PCH=OFF
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 cmake --build build-nounity -j3
```

`<debug-preset>` is `dev` in Lambent and the libraries, and `debug` in PlasmaZones. Afterglow's own tree does
not build as unity, so this gate does not apply to it. A repository with no
`ENABLE_PCH` option reports it as an unused variable, which is harmless.

## Pinned dependencies

- Each repository pins its dependencies (the libraries it uses, Luau, jsoncons and others) in
  `cmake/<Project>Dependencies.cmake`. The first configure of a fresh tree downloads the pinned archives with CPM
  into `.cache/cpm`, which every build dir of that repository shares.
- With no network, pass `-DPHOSPHOR_DEPS_ARCHIVES=<dir>` holding the archives, filled beforehand with
  `cmake -DPHOSPHOR_DEPS_FETCH=<dir> -P cmake/<Project>Dependencies.cmake`. Afterglow names them
  `AFTERGLOW_DEPS_ARCHIVES` and `AFTERGLOW_DEPS_FETCH`.
- To build against a library change before the pin moves, use the `workspace` superbuild, or pass
  `-DCPM_<library>_SOURCE=<checkout>` to one build dir.
- Move a pin after the library change merges: VERSION, URL, FILE and SHA256 together, with the hash of the
  downloaded archive. Repeat it in `packaging/nix/package.nix` where the repository has one.
- Never edit a checkout that a build dir compiles from. A library change goes through that library's branch and
  pull request.

## Never install

Never install (`cmake --install`, the `install` target), and never use `sudo`. The user installs the apps. The one
exception: `cmake --install` into a temporary directory (`--prefix` or `DESTDIR` under `/tmp`) to check the install
layout.

Never `pkill` or `killall` an app's process name: that kills the user's real desktop process. Kill only test
binaries from the build tree, by PID.

## Subagents never build

Reviewer and audit subagents must **not** run `ctest`, `cmake --build`, extra `cmake` configures or the test
binaries. Six agents doing that at the same time once spawned enough daemon activations to crash the machine, and
parallel builds give results that nobody can attribute. Reviewers read and grep. A single compiled standalone probe
is fine. The main session runs the build and the suite once, serially.

## Green does not mean it works

A passing suite is not evidence that a change in behavior is right. Invariants that matter have been caught by live
verification and by invariant checks, not by the unit suite. Verify a visible or behavioral change live, as the
repository's verify skill or `CLAUDE.md` says (`plasmazones:verify-live`, `afterglow:verify-live`, Lambent's
`scripts/nested-shell/`). The commit message says what you ran.

---
name: build
description: "Configure, build and test Afterglow, on top of phosphor-works:build. Covers the build directories, aglow and aglow-mux, the Phosphor libraries built from the pinned phosphor-libs commit, warnings, the CTest suite, and which tests need a GPU or a nested KWin. Use when: build, rebuild, run the tests, run ctest, does it compile, is it green, before committing."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Build and test Afterglow

Follow `phosphor-works:build` first: the memory cap, one build at a time with 3 jobs, the warning check,
`--no-tests=error`, never install, and why subagents never build. This skill adds what is Afterglow's own.
`docs/BUILD.md` and `docs/TESTING.md` are the user-facing versions of this procedure.

## The build directories

Add `AFTERGLOW_[A-Z_]+` to the `grep` of the shared skill to see each directory's options.

| Directory | Type | Tools | Use |
| --- | --- | --- | --- |
| `build` | Debug (`dev` preset) | ON | Day-to-day work. All the commands below use it. The script tests that hold a handler to its CPU-time limit have thin margins at `-O0`: when one fails here, run it in `build-relwithdebinfo` before you look for a bug. |
| `build-relwithdebinfo` | RelWithDebInfo (`relwithdebinfo` preset) | ON | Optimized with debug info, as CI and the packages build |
| `build-release` | Release | ON | Performance numbers and release checks |
| `build-prof` | RelWithDebInfo | ON | Profiling with `perf` |
| `build-fuzz` | RelWithDebInfo, clang for C and C++, `AFTERGLOW_BUILD_FUZZERS=ON`, `BUILD_TESTING=OFF` | OFF | The libFuzzer targets `afterglow_vtfuzz`, `afterglow_protofuzz`, `afterglow_imagefuzz` and `afterglow_muxfuzz`, and the seed writer `afterglow_imagefuzz_seeds`, only. Build them by name: the other binaries are not supported there (zlib-ng and the image codecs are instrumented in place). The fuzz option turns `aglow` off. Make it when you fuzz, with the commands in `docs/TESTING.md`. |
| `build-asan` | Debug with ASan and UBSan at `-O1` (`asan` preset) | — | Make it when you look for memory errors, and before a PR that changes a parser, a protocol or a pane's memory. Build it with `-j2`: at `-j4` the compiles hit the 6 GB cap. `docs/TESTING.md` "Sanitizer build" has the three runs (errors, leaks with `-LE gpu`, native). `aglow` links dynamically there, and `aglow_static` is left out. |

## aglow

`AFTERGLOW_AGLOW_ONLY=ON` builds only `libs/afterglow-proto`, `libs/afterglow-image`, `tools/aglow` and, with
`AFTERGLOW_BUILD_MUX` (on by default), `libs/afterglow-vt`, `libs/afterglow-pty`, phosphor-channel and `mux/`: no Qt,
and of the Phosphor checkout only phosphor-channel (none with `AFTERGLOW_BUILD_MUX=OFF`). It installs `bin/aglow`,
its completions and its notices in `share/licenses/aglow`, and `bin/aglow-mux`, its private libraries in
`lib/phosphor-works/afterglow` and its notices in `share/licenses/aglow-mux`. `docs/BUILD.md` has the procedure.

`AFTERGLOW_BUILD_AGLOW` is on by default. `aglow` links statically, so the configuration needs `libc.a` and
`libstdc++.a` (Fedora: `glibc-static` and `libstdc++-static`). Without them, the configuration stops with a message
that names the packages. In a build of `aglow` alone (`AFTERGLOW_AGLOW_ONLY`) the message only names the packages:
that build cannot turn `aglow` off. Do not install them: tell the user, or configure with
`-DAFTERGLOW_BUILD_AGLOW=OFF`. Then the `aglow` tests are left out. The `aglow dnd` tests of `afterglow_dnd_tests`
and of the native suite skip, and so do the `RunBinaryTest.*` tests of `afterglow_command_tests` and the `sshd`
test of `afterglow_remote_tests` (`RemoteCommandsTest.OpenSshForwardsAsTheDesignExpectsAndAglowRunWorksThroughIt`).
So do the native session tests
`AglowRunInASessionPaneRunsTheCommandsOfItsWindow`, `AglowRunInASessionOfAnotherHostGetsOnlyRemoteCommands` and
`AnSshSessionInASessionPaneRunsRemoteCommandsThroughTheDaemon`.
`aglow` builds next to `afterglow` (`build/afterglow/aglow`), and building `afterglow` builds it too.

`libs/afterglow-image` builds libpng, libjpeg-turbo, libwebp and Little CMS from their pinned archives into `aglow` and
`aglow-mux`, also with `-DAFTERGLOW_BUILD_AGLOW=OFF`. No image library of the system is used. libjpeg-turbo
builds with its own CMake during the build, in `build/_afterglow_deps/libjpeg-turbo-build`. When that step fails,
its output is in the logs under `build/_afterglow_deps/libjpeg-turbo-steps`. It uses NASM when NASM is installed.
It runs `AFTERGLOW_CODEC_BUILD_JOBS` jobs (2 by default) beside the main build: count them in the memory cap.

`AFTERGLOW_BUILD_TOOLS=ON` builds `afterglow_renderpng`, `afterglow_headless`, `afterglow_tuifuzz`,
`afterglow_vtbench` and `afterglow_native_bench`, and with `BUILD_TESTING` also `afterglow_screen_checks_tests`.
Shader previews, `aglow_icat_render` and `afterglow_headless_runner` need it. The renderer tests (`Render.*`) do
not: `BUILD_TESTING` builds them.

## aglow-mux

`aglow-mux` (`mux/`) is the session daemon of `afterglow mux`. It has no Qt and links `afterglow-vt`,
`afterglow-pty`, `afterglow-proto`, phosphor-channel and `afterglow-image`, which its image decoder uses. It builds
next to `afterglow` (`build/afterglow/aglow-mux`), because `afterglow mux` runs the daemon from its own directory,
and building `afterglow` builds it too. A build of `aglow` alone (`AFTERGLOW_AGLOW_ONLY`) builds it into `mux/` of
its build directory, unless `AFTERGLOW_BUILD_MUX` is off. Its tests are `afterglow_mux_tests` (`Mux.*`) and the
client tests of `afterglow mux` in `afterglow_mux_command_tests` (`MuxCommandTest.*`). `docs/TESTING.md` "Mux daemon
tests" has the command that runs them with the other tests of sessions. With `-j4` it takes about 15 seconds. Most of
that time is the start wait of `Mux.MuxDaemon.ADaemonThatNobodyReachesEnds`. Without `-j`, the run takes about 50
seconds. `afterglow mux new` without `--detach`, `afterglow mux attach` and `afterglow --mux-attach` also open a
window: the native tests show sessions with a daemon of their own (`mux/tests/TestDaemon.h`).

The rule "Never touch the user's running Afterglow" in `CLAUDE.md` lists what reaches the user's mux daemon and its
sessions, also from a nested KWin: `afterglow mux` (every command but `--help`), `afterglow ctl --session`,
`afterglow mcp` (every run but `--help`), `aglow-mux` (every run but `--help` and `--version`), `--mux-attach`, a
project with `"session": true` and `launch.newWindow` with a `session`. The `--ssh` option, `--mux-host` and a
`sessionHost` reach the daemon of another host with the user's ssh keys. Run them only with a private
`XDG_RUNTIME_DIR` and `XDG_STATE_HOME` under `/tmp`, as the tests do (they also give a `HOME` of their own), and kill
the sessions that you made. `afterglow mcp` also needs a private `XDG_CONFIG_HOME` and `HOME`: `save_project` writes
to the `projects` folder of the configuration. Never register an MCP server from `build/` with an MCP client: it
starts an `aglow-mux` from `build/`, and the next build breaks it. Never stop, restart or mask the user's
`aglow-mux.service` or `afterglow-mux.service`, and never remove the files in the user's `aglow-mux` and
`afterglow-mux` directories.

## The Phosphor libraries

`cmake/AfterglowPhosphor.cmake` adds the phosphor-libs commit that `cmake/AfterglowDependencies.cmake` pins as a
subproject, embedded in Afterglow (`PHOSPHOR_EMBED_APP`). CPM downloads that commit's archive into the CPM cache. A
build directory can name a phosphor-libs checkout instead with `-DCPM_phosphor-libs_SOURCE`, to build against a change
before the pin moves. Each build directory keeps its own value, and the `grep` at the top of this skill shows it. When a build
that names a checkout fails or changes for no reason in this repository, check the checkout first:

| Condition | Check | Action |
| --- | --- | --- |
| The checkout is not at the pinned commit, or has uncommitted work. | `git -C <checkout> status -sb` and `git -C <checkout> rev-parse HEAD` | Tell the user. |
| The build fails in a Phosphor call. | Compare the call with the Phosphor header in the tree that the build uses. | If Afterglow calls a newer API, move the pin to a phosphor-libs commit that has it, in the same change: VERSION, URL, FILE and SHA256 together, with the hash of the downloaded archive. Tell the user. |

- Never edit a checkout that a build directory compiles from. Update one only with the user's approval. A Phosphor
  change goes through a phosphor-libs branch and pull request. Tell the user what Phosphor needs.
- The renderer uses Qt private APIs. After a Qt update, rebuild everything in the capped scope:
  `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 cmake --build build --clean-first -j3`.
- The pinned archives are phosphor-libs, zlib-ng, xxHash, libpng, libjpeg-turbo, libwebp and Little CMS from
  `cmake/AfterglowDependencies.cmake`, and Luau and jsoncons from `cmake/PhosphorDependencies.cmake` in the pinned
  phosphor-libs tree. Offline, fill the archive directory with
  `cmake -DPHOSPHOR_DEPS_FETCH=<dir> -P cmake/AfterglowDependencies.cmake`.

## Build

The presets set no job count: pass `-j3`, as the shared skill says.

- The session runs in the cgroup of the user's Afterglow. When memory runs out, systemd-oomd kills that whole unit
  with every window of the user. The capped scope of the shared skill is not optional here.
- `QT_NO_KEYWORDS` is on for the whole project: write `Q_EMIT`, `Q_SIGNALS` and `Q_SLOTS`. `QT_NO_CAST_FROM_ASCII`
  is on for the application targets and `afterglow-render`: a raw `"string"` into a `QString` does not compile
  there. Use `QStringLiteral` or `QLatin1String`, also in tests that link those targets.
- An install into a directory under the build tree, as `aglow_only_build` does, is also allowed for a layout check.

## Test

The suite has about 2,000 tests. All of them must pass. Use `-R PATTERN` while you work, and run the whole suite
before a commit.

- `aglow_only_build` (label `slow`) configures `aglow` alone with Qt hidden and no Phosphor directory, then
  configures, builds and installs `aglow` and `aglow-mux` alone (`AFTERGLOW_AGLOW_ONLY`) in
  `build/tools/aglow/aglow-only`, with Qt hidden and the Phosphor checkout of `build`. It compiles zlib-ng, the image
  codecs, afterglow-vt, afterglow-pty, phosphor-channel and mux/ again, configures their tests without building them,
  and takes some minutes. `-LE slow` leaves it out while you work. The whole suite before a commit includes it.
- The renderer tests (`libs/afterglow-render/tests`), `afterglow/tests/PopupLookTest.cpp` and
  `afterglow/tests/PointerMapTest.cpp` (`afterglow_pointer_map_tests`) need a Wayland display and a working Vulkan
  driver. They skip only on a machine with no Wayland display or no Vulkan. A device that cannot be made fails them.
  They take turns on the GPU (`RESOURCE_LOCK gpu`, also `aglow_icat_render`): each test process makes its own device,
  and several at once ran out of device memory beside the desktop's own use of the GPU. Give a new GPU test the same
  lock.
- The native window tests (`afterglow_native_tests`, the `Shaders/` tests included) are not in CTest by default
  (`AFTERGLOW_NATIVE_TESTS=OFF`).
  They need a nested KWin. Use the `afterglow:verify-live` skill to run them.
- CTest runs some Python tests: `completion_test.py` (`afterglow_shell_completion`), `mcp_session.py`
  (`afterglow_mcp_session`: `afterglow mcp` against a daemon of its own; `afterglow_mcp_session_window`: its case with
  a window in a headless KWin, which takes the GPU lock and skips with 77 without KWin or Vulkan), the relays of
  `kitty_transfer_interop.py`, `tools/generate-reference.py --check`, the scripts in `tools/aglow/tests`, and
  `test_headless.py` (`afterglow_headless_runner`), `test_tuifuzz.py` and `kitten_icat.py` in `tools/conformance`. With
  `AFTERGLOW_NATIVE_TESTS=ON` it also runs `native_window_acceptance.py` and `kitty_transfer_interop.py --kitty`. The
  other Python suites in `afterglow/tests/*.py` are separate: `desktop_acceptance.py`, `scene_acceptance.py`,
  `shader_parameters_smoke.py`, `project_smoke.py` and the two navigator tests. Run the ones that cover the area that
  you changed (`docs/TESTING.md` lists them).

## Generated files

| File | Command |
| --- | --- |
| `docs/CONFIGURATION.md` | `python3 tools/generate-reference.py build/afterglow/afterglow` after a change to a setting, its default or its description |
| `libs/afterglow-vt/src/UnicodeTables.inc` | `python3 -I tools/gen_unicode_tables.py <ucd-dir> libs/afterglow-vt/src/UnicodeTables.inc` |

The guard hook refuses a direct edit of these files.

## Green does not mean it works

A passing suite does not prove that a visible change looks right or that an animation settles. For anything that
renders, check it with `afterglow_renderpng` (the `afterglow:shader-pack` skill) or in a nested KWin (`afterglow:verify-live`).

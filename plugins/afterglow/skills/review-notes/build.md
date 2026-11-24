<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Afterglow build, test, tooling and documentation review notes

Read by `phosphor-works:build-reviewer` in addition to its own instructions.

## Partition coverage and hand-offs

- Covers every CMakeLists.txt (`mux/CMakeLists.txt` and `mux/tests/CMakeLists.txt` included) and `cmake/**`: `AfterglowPhosphor.cmake`, and `AfterglowDependencies.cmake` with the zlib-ng, xxHash, libpng, libjpeg-turbo, libwebp and Little CMS archive pins, with `tools/aglow/CheckStatic.cmake` and `tools/aglow/AglowOnlyCheck.cmake`.
- Also covers `libs/afterglow-image/notices/**`, `tools/aglow/notices/**`, `CMakePresets.json`, `REUSE.toml` and `LICENSES/`.
- Test code: the GTest and Python harnesses in `afterglow/tests/**` (`mcp_session.py`, the runner of `afterglow mcp` against a private daemon, and `ctl_run.py`, the runner of `afterglow ctl run` and `wait`, included), `libs/*/tests/**`, `mux/tests/**` and `tools/aglow/tests/**`.
- Tools and data: `tools/bench/**` with the recorded results in `data/benchmarks/**`, `tools/*.py`, `tools/headless_native.py`, `data/*.desktop`, the AppStream metainfo and `data/icons/**`.
- Documents: `README.md`, `CHANGELOG.md`, `docs/**`, and the `README.md`, `PERFORMANCE.md`, `validation-results.json` and `preview.webp` of the `examples/glasshouse` and `examples/phosphor` demos.
- Session tooling: `CLAUDE.md`, `.gitignore`, `.mcp.json` and `.claude/settings.json`. The guard hook, the skills and the reviewer definitions are in the workspace repo's Claude plugins.
- docs/WRITING.md is the authority on prose in this repo.
- Read `.cpp` files over 800 lines in chunks.

Hand-offs:

| Subject | Reviewer |
| --- | --- |
| Terminal core, the `libs/afterglow-proto` wire formats, the `libs/afterglow-image` decoders, `examples/compatibility/**`, `data/terminfo/**`, the C++ of `tools/conformance` and `tools/fuzz` | `afterglow:vt-reviewer` |
| PTY, shell, desktop, D-Bus, audio, app, the control and commands sockets, the `libs/afterglow-proto` transfer and drag-and-drop formats, phosphor-ipc client and server, the mux daemon, `afterglow mux`, `afterglow/src/mux/**`, `afterglow mcp`, `afterglow/src/mcp/**`, aglow, the shell completions, `afterglow/src/main.cpp`, the demos' `bin/*`, the technical accuracy of docs/MCP.md | `afterglow:platform-reviewer` |
| Renderer, the C++ in `tools/render` | `afterglow:render-reviewer` |
| TerminalWindow, panes, input, QML, `examples/projects/**` | `afterglow:window-reviewer` |
| GLSL packs | `phosphor-works:shader-reviewer` |
| Luau, the demos' `scripts/*.luau`, the technical accuracy of docs/SCRIPTING.md and docs/PACKAGES.md | `phosphor-works:luau-reviewer` |
| Settings and themes, the demos' `config/*.json`, the content of docs/CONFIGURATION.md (generated) | `phosphor-works:config-reviewer` |

What a test asserts about its subject goes to that subject's owner. The CMakeLists.txt of `tools/render`, `tools/conformance` and `tools/fuzz` stay with the build reviewer. The build reviewer owns the prose rules in every document.

## Evidence example

- "`afterglow_app` sets `QT_NO_CAST_FROM_ASCII` PUBLIC, so `afterglow_native_tests` inherits it (afterglow/CMakeLists.txt:155)" is a finding. "The bench will not compile" is a hypothesis.

## Build

- **Phosphor**: `cmake/AfterglowPhosphor.cmake` adds phosphor-libs from the commit that `cmake/AfterglowDependencies.cmake` pins (or from `AFTERGLOW_PHOSPHOR_LIBS_DIR` when set) in dependency order, `EXCLUDE_FROM_ALL`, with `BUILD_TESTING` off and phosphor's own `install()` rules suppressed by a macro. A new phosphor library needs its place in that list AND in the private `install(TARGETS ...)` list in afterglow/CMakeLists.txt (`lib/phosphor-works/afterglow`, reached through the RPATH).
- **aglow-only build**: the build of aglow and aglow-mux alone (`AFTERGLOW_AGLOW_ONLY`) takes the early branch of AfterglowPhosphor.cmake, which adds only phosphor-channel and returns. A library that aglow-mux links joins that branch too, and `AFTERGLOW_MUX_PRIVATE_LIBS` (root CMakeLists.txt). aglow-mux installs that list itself in that build (mux/CMakeLists.txt), and afterglow's private list includes it.
- **Pinned archives**: `cmake/AfterglowDependencies.cmake` pins phosphor-libs (a commit), zlib-ng, xxHash, libpng, libjpeg-turbo, libwebp and Little CMS (VERSION, URL, FILE and SHA256 change together). It fetches them through CPM, or from `AFTERGLOW_DEPS_ARCHIVES` without network and without loading CPM. The pinned phosphor-libs tree's `cmake/PhosphorDependencies.cmake` pins Luau and jsoncons.
- **Include order**: the root `CMakeLists.txt` includes `AfterglowDependencies.cmake` first at the top scope (CPM keeps its state in the including scope's variables), then `AfterglowPhosphor.cmake`, which fetches phosphor-libs and includes its pin module. So the CPM cache is Afterglow's `.cache/cpm`. With only `AFTERGLOW_DEPS_ARCHIVES`, `AfterglowPhosphor.cmake` sets `PHOSPHOR_DEPS_ARCHIVES` to the same directory, which the fetch script fills with both sets.
- **Codecs**: `libs/afterglow-image/CMakeLists.txt` compiles libpng and libwebp from source lists. It builds libjpeg-turbo with its own CMake through `ExternalProject_Add` (compiler, flags, sysroot and `AFTERGLOW_CODEC_BUILD_JOBS` forwarded).
- **Static aglow**: `aglow` links `-static-pie` or `-static` (`tools/aglow/CheckStatic.cmake`, the `aglow_static` test). `aglow_only_build` (`tools/aglow/AglowOnlyCheck.cmake`) builds it alone, with `aglow-mux` and its private libraries, and without the Phosphor checkout when `AFTERGLOW_BUILD_MUX` is off.
- **Notices**: each third-party library compiled into the binaries installs its notice (`afterglow_install_bundled_notices` in AfterglowDependencies.cmake). The set is `LICENSE.zlib-ng`, `LICENSE.xxHash`, `LICENSE.libpng`, `LICENSE.libjpeg-turbo` with `README.ijg` and `NOTICE.IJG`, `LICENSE.libwebp` with `PATENTS.libwebp`, `LICENSE.lcms2`, `LICENSE.Unicode` for the Unicode tables of libs/afterglow-vt, and the glibc and libstdc++ notices of `tools/aglow/notices` for a static `aglow`. `LICENSE.jsoncons` (the BSL text, then the MIT notices of `grisu3.hpp` and `a5hash.hpp`) installs unless `PHOSPHORFSLOADER_USE_SYSTEM_JSONCONS`: phosphor-fsloader writes the file into its binary directory at configure, and afterglow/CMakeLists.txt installs it from there, because the phosphor rule that installs it is skipped. `LICENSE.Luau` with `LICENSE.Lua` installs unless `PHOSPHOR_SYSTEM_LUAU`. A missing notice is a configure error, not a skipped rule.
- zlib-ng's `include(CPack)` must write into its own build directory (`CPACK_OUTPUT_CONFIG_FILE`), never the top-level `CPackConfig.cmake`.
- **Global settings**: `QT_NO_KEYWORDS` everywhere, `-Wall -Wextra -Wpedantic`, hidden visibility. `QT_NO_CAST_FROM_ASCII` is set per target and PUBLIC on `afterglow_app`, so the native tests and native bench inherit it.
- **Targets**: `afterglow_shaders`, `afterglow_config`, `afterglow_shell`, `afterglow_audio` and `afterglow_scripting` are static libraries shared with their tests. The Luau prelude is a `qt_add_resources` file. `afterglow_add_chrome()` builds the QML module for each executable, and every QML file must be listed or the error comes at run time. `mux/` builds `afterglow_mux_protocol` (linked by the application too), `afterglow_mux_image` and `afterglow_mux_daemon`, static libraries that `aglow-mux` and `afterglow_mux_tests` share. Source-tree paths reach tests through compile definitions (`AFTERGLOW_EXAMPLE_PACKAGES`, `AFTERGLOW_THEME_DIR`).
- **Options**:

| Option | Effect |
| --- | --- |
| `AFTERGLOW_BUILD_TOOLS` | Bench, render, conformance. |
| `AFTERGLOW_BUILD_AGLOW` | On by default. Without it `afterglow` has no `run`, `transfer`, `dnd`, `icat` or `clipboard`. |
| `AFTERGLOW_BUILD_FUZZERS` | Needs clang for C and C++. |
| `AFTERGLOW_BUILD_VTDIFF` | Needs libghostty-vt in `CMAKE_PREFIX_PATH`. |
| `AFTERGLOW_NATIVE_TESTS` | Nested KWin. |
| `AFTERGLOW_AGLOW_ONLY` | aglow and aglow-mux alone, no Qt. The configuration stops when `AFTERGLOW_BUILD_AGLOW` is off or a tool, fuzzer, vtdiff or native-test option is on. |
| `AFTERGLOW_BUILD_MUX` | Shown only with `AFTERGLOW_AGLOW_ONLY`, on by default. aglow-mux needs PCRE2 and the Phosphor checkout. Without the checkout the configuration stops with a `FATAL_ERROR` that names `AFTERGLOW_BUILD_MUX` off as the way out. |

- docs/BUILD.md's required packages must match every `find_package`/`pkg_check_modules`, including private Qt modules.
- **Install**: data installs by directory (`shaders`, `themes`, `shell-integration`, `api/afterglow.d.luau`). The root `examples/` directory does not install. The app id `${AFTERGLOW_APP_ID}` (`com.phosphorworks.Afterglow`) names the .desktop file, the metainfo, the icon and the desktop entry the code sends.

## Tests and tools

- GTest with `gtest_discover_tests`. A test isolates `XDG_CONFIG_HOME`, `HOME`, `XDG_RUNTIME_DIR` (sockets and their locks), `XDG_STATE_HOME` (the second socket of the mux daemon), the session bus, and the inherited `AFTERGLOW_SOCKET`, `AFTERGLOW_PANE_ID` and `AFTERGLOW_SESSION`. With `AFTERGLOW_SESSION` set, `afterglow ctl` takes `AFTERGLOW_SOCKET` as the mux daemon's. A test restores the environment in `TearDown`.
- The runners start `dbus-run-session` for the native tests, which run in the nested KWin of `nested_desktop.py` with `QT_QPA_PLATFORMTHEME=generic`. Offscreen tests set `QT_QPA_PLATFORM=offscreen`.
- `tools/generate-reference.py` writes docs/CONFIGURATION.md from `afterglow --config-reference`.
- `tools/bench`: dimensions are fixed under host tiling. Recorded results in `data/benchmarks` keep their test conditions.

## Licensing and prose

- `afterglow/**`, `mux/**` and example scripts are GPL-3.0-or-later. `libs/**` including their `tests/` are LGPL-2.1-or-later.
- A tool follows what it links. VT-only tools such as `vtbench.cpp`, `tools/conformance`, the rest of `tools/fuzz` and `gen_unicode_tables.py` are LGPL. App tools are GPL, and so is `tools/fuzz/muxfuzz.cpp`, which compiles `mux/`.
- New shader packs are LGPL-2.1-or-later, but Feedback Glow, Depth Trails and Mesh Reactor are GPL-3.0-or-later. Check the existing header before you flag a license.
- **CHANGELOG.md**: one `## Unreleased` section, written as the first release. No migration guides, and no "now", "previously" or "renamed from" wording. The project is unreleased, so docs never describe an upgrade path.

## Known past-bug shapes

- Test code broke under inherited `QT_NO_CAST_FROM_ASCII` and warned on partial designated initializers and an unbraced `if` around GTest macros. Check new test code against the definitions its target inherits and against `-Wextra`.
- Native tests activated the desktop portal through the platform theme. Harness environments set every variable that reaches the user's session.
- The fuzz target globbed VT sources but did not link PCRE2, and `op % 4` picked one selection mode. A target that globs sources must link every library they use. Fuzz selectors must reach every branch.
- `esctest.sh` hid runner failures with `|| true` and accepted a run without a summary. Responder paths were unquoted. Harnesses fail on incomplete runs and quote every path.
- The native benchmark window was resized by host tiling. Measurements fix their dimensions.
- BUILD.md omitted `ShaderToolsPrivate`. Documented requirements match the CMake calls.
- `gen_unicode_tables.py` used `assert` as a capacity guard. Use explicit errors.
- A migration guide, audit material and a docs section in the wrong document reached the repository. Check each section's home and the first-release rule.

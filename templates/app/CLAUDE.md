<!-- SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# @REPO@

@DESCRIPTION@ Qt 6, C++20 and QML. Application ID `@APPID@` (the `.desktop` file, the AppStream id and the
icon).

The rules every phosphor-works repository follows come from the workspace repository, imported below. This file adds
@REPO@'s own. The shared Claude Code tooling comes from the `phosphor-works` plugin, which `.claude/settings.json`
enables and `workspace/tools/setup` installs.

@../workspace/claude/conventions.md

## Layout

| Folder | What it is |
| --- | --- |
| `@app@/src/` | The program: `main.cpp` sets the application up and loads the window |
| `@app@/qml/` | The `@AppNs@` QML module (`@app@_ui`, a static library that the program and the tests link). List every QML file in its `qt_add_qml_module` |
| `@app@/tests/` | Qt Test cases of the application, offscreen |
| `@app@/data/` | The `.desktop` file and the AppStream metadata, which install with the program |
| `libs/@app@-core/` | `@AppNs@Core`: code that another program could use, as a library of its own (`LGPL-2.1-or-later`) |

- The application, its tests and its tools are `GPL-3.0-or-later`. `libs/**` is `LGPL-2.1-or-later`, its tests
  included. The `.desktop` file and the AppStream metadata are `CC0-1.0`. `REUSE.toml` licenses the files that cannot
  hold a header, and the license texts are in `LICENSES/`.
- A new library in `libs/` has the shape of `libs/@app@-core`: its own `CMakeLists.txt`, `project()`, `include/`,
  `src/`, `tests/` and find_package config. Add it in the root `CMakeLists.txt` before the application.
- The `.desktop` file, the AppStream metadata, UI strings and `CHANGELOG.md` are user-facing text. A user-visible
  change gets a line under `## Unreleased` in `CHANGELOG.md`.

## Build and test

- `cmake --workflow --preset dev` configures into `build/`, builds phosphor-libs and this tree, and tests. Follow
  `phosphor-works:build` for the memory cap, jobs and warnings.
- CI is the shared C++ CI of the workspace repository (`cpp-ci.yml`): the `dev` preset on Arch, with a warning
  failing the build, and clang-format and qmlformat on every tracked file. There is no flake yet, so the Nix jobs are
  off. Add `flake.nix` and `nix/package.nix` and drop `nix: false` from `ci.yml` to turn them on.
- `cmake/@PROJECT@Dependencies.cmake` pins the phosphor-libs commit (VERSION, URL, FILE and SHA256, changed together)
  and CPM.cmake. `-DCPM_phosphor-libs_SOURCE=<dir>` builds against a local checkout, and the workspace superbuild
  (`cmake --workflow --preset dev` in `../workspace`) builds it with every sibling library.

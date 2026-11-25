---
name: review-notes
description: "PlasmaZones' known past-bug shapes and code-specific checks for each review domain. The shared phosphor-works reviewers read the file for their domain."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# PlasmaZones review notes

Each file in this directory holds, for one review domain, the bug shapes that PlasmaZones has had and the checks
that apply only to its code. A shared phosphor-works reviewer reads the file for its domain before it reviews
PlasmaZones code, and applies it on top of its general checks.

| Domain | File |
| --- | --- |
| C++ and Qt: object lifetimes, signals, threads, the daemon and the engines | `cpp-qt.md` |
| QML: the settings app, the editor and the overlays | `qml.md` |
| Wayland: layer-shell, protocols and the KWin effect's compositor side | `wayland.md` |
| Build: CMake, presets, tests, packaging and data files | `build.md` |
| Config: settings, the store, schema and migration | `config.md` |
| Shaders: GLSL packs, their metadata and the uniform contract | `shader.md` |
| Luau: tiling algorithms and the script API | `luau.md` |

Read only the file for the domain of the review. When a review finds a shape that recurs, add it to that file
(`phosphor-works:record-lesson`).

---
name: review-notes
description: "Afterglow's known past-bug shapes and code-specific checks for each review domain. The shared phosphor-works reviewers read the file for their domain."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Afterglow review notes

Each file in this directory holds, for one review domain, the bug shapes that Afterglow has had and the checks that
apply only to its code. A shared phosphor-works reviewer reads the file for its domain before it reviews Afterglow
code, and applies it on top of its general checks.

| Domain | File |
| --- | --- |
| C++ and Qt: object lifetimes, signals, threads, the terminal core, the mux and the renderer | `cpp-qt.md` |
| QML: the window chrome, popups and the overview | `qml.md` |
| Build: CMake, presets, tests, `aglow` and packaging | `build.md` |
| Config: settings, the schema and the generated reference | `config.md` |
| Shaders: GLSL packs, their metadata and the contract headers | `shader.md` |
| Luau: the script API and packages | `luau.md` |

Read only the file for the domain of the review. When a review finds a shape that recurs, add it to that file
(`phosphor-works:record-lesson`).

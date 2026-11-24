---
id: a-new-engine-library-needs-the-qml-firewall-list
title: A new engine library must join PHOSPHOR_ENGINE_TARGETS
repos: [phosphor-engine-libs]
domains: [build, cmake]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

The engine QML check in phosphor-engine-libs' root CMakeLists checks only the targets in `PHOSPHOR_ENGINE_TARGETS`.
A wrong name in the list fails the configure, but a library left out of it is never checked for a Qml or Quick
link.

---
id: a-qml-file-needs-its-resource-alias
title: A QML file without QT_RESOURCE_ALIAS lands at a nested resource path
repos: [phosphor-shell-libs, phosphor-components]
domains: [qml]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

A QML file in a module whose `QT_RESOURCE_ALIAS` is not set to its basename gets a resource path nested twice. The
module's singletons then do not resolve from inside the module. Set the alias on every file the module lists.

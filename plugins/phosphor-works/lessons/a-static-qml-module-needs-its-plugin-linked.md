---
id: a-static-qml-module-needs-its-plugin-linked
title: A static QML module needs its Qmlplugin target linked too
repos: [phosphor-shell-libs, phosphor-components, PlasmaZones, Lambent]
domains: [qml, build]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Linking only the backing library of a static QML module (`<X>`) builds, but `import` fails at run time. Link the
`<X>Qmlplugin` target as well, so the plugin registers.

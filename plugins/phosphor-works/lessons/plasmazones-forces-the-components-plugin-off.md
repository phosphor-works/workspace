---
id: plasmazones-forces-the-components-plugin-off
title: PlasmaZones turns off the installed Phosphor.Components plugin for the whole tree
repos: [phosphor-components, PlasmaZones, workspace]
domains: [build, qml]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

PlasmaZones links Phosphor.Components as a static module and sets `PHOSPHOR_COMPONENTS_QML_INSTALL` OFF as a forced
cache value. In the workspace superbuild, the installed plugin is therefore never built. Test the plugin build in
phosphor-components on its own.

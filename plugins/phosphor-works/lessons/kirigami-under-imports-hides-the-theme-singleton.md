---
id: kirigami-under-imports-hides-the-theme-singleton
title: org.kde.kirigami under IMPORTS hides the Phosphor.Theme singleton
repos: [phosphor-shell-libs, Lambent]
domains: [qml]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

In `qt_add_qml_module`, listing `org.kde.kirigami` under `IMPORTS` made Kirigami's `Theme` shadow the
`Phosphor.Theme` `Theme` singleton, and every colour token read undefined. Put it under `DEPENDENCIES` instead.

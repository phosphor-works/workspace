---
id: async-qml-component-ready-before-create
title: An asynchronous QML component that is ready before create() makes no object
repos: [all]
domains: [qml, crash]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Afterglow's native suite segfaulted in 3 of 8 runs, in Qt, while a window built its chrome. A component from
`loadFromModule(..., Asynchronous)` that was ready before `create(QQmlIncubator&)` took Qt 6.12's C++-type path and
made no object. A window freed while its own load ran got a late completion into freed memory. Now the chrome loads
by URL, once for each Application. For a crash in some runs only, read the core with `coredumpctl` and write a test
that makes it happen every time.

---
id: qhash-value-default-is-evaluated-every-call
title: QHash::value(key, f()) evaluates f() on every call
repos: [all]
domains: [cpp-qt]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

The default is an ordinary argument, so if `f` inserts into the same container, the lookup returns what `f` just
wrote. Use `constFind` and resolve only on a miss.

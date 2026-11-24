---
id: a-new-validation-gate-turns-disagreement-into-data-loss
title: A new validation gate turns a producer and consumer disagreement into lost data
repos: [all]
domains: [config, design]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Before you add a schema check or gate, check every producer against it. One gate rejected saves that clients still
reported as successful.

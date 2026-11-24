---
id: agents-sharing-one-working-tree-undo-each-other
title: Agents that share one working tree undo each other
repos: [all]
domains: [git, agents]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`git stash`, `reset --hard` and `checkout`, run to check a pre-existing failure, once wiped other agents'
uncommitted work. Mutation checks run in a separate worktree or scratch copy, and nobody runs checkout, restore,
stash or reset in a shared tree.

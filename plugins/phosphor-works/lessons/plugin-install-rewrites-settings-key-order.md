---
id: plugin-install-rewrites-settings-key-order
title: claude plugin install rewrites a repo's settings.json in its own key order
repos: [all]
domains: [claude]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`claude plugin install --scope project` writes `.claude/settings.json` with its keys in its own order
(`permissions`, `enabledMcpjsonServers`, `enabledPlugins`, `extraKnownMarketplaces`). A file committed in another
order changes on every install. Run the install once and commit the file it leaves.

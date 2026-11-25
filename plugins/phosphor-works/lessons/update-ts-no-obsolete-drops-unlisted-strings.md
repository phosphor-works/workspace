---
id: update-ts-no-obsolete-drops-unlisted-strings
title: update-ts with -no-obsolete drops every string missing from the QML list
repos: [phosphor-components]
domains: [i18n]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`phosphor-components-update-ts` runs `lupdate -no-obsolete`. A QML file left out of the module's file list loses
its strings from every catalog on the next update, translations included.

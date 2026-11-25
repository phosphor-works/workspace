---
id: a-public-qml-link-breaks-the-engine-firewall
title: A PUBLIC Qt6::Qml link on a library the engines reach breaks phosphor-engine-libs
repos: [phosphor-libs, phosphor-engine-libs]
domains: [build, cmake]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

phosphor-engine-libs fails to configure when an engine reaches `Qt6::Qml` or `Qt6::Quick` anywhere in its link
closure. A new PUBLIC Qml link on a core library the engines use (`phosphor-registry`, `phosphor-layout-api`)
breaks the engine repo, not phosphor-libs. Link Qml PRIVATE, or keep it out of those libraries.

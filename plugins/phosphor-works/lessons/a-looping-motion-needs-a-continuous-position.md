---
id: a-looping-motion-needs-a-continuous-position
title: A motion that loops needs a continuous position
repos: [all]
domains: [animation]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Wrapping the target of a looping motion (Afterglow's overview ring) made the highlight jump back, and two cards
flickered at the seam. Keep the position continuous and wrap only when you draw it.

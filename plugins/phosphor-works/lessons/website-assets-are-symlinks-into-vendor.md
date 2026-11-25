---
id: website-assets-are-symlinks-into-vendor
title: The website's brand assets are symlinks into the gitignored vendor/
repos: [website]
domains: [build]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`public/brand/assets` and `public/palette/phosphor.toml` point into `vendor/`, which `npm run fetch:branding` fills
from the pinned branding release. Until it runs, greps over the tree warn about broken links and the palette page
has no data.

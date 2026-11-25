---
id: surface-packs-check-does-not-compile-glsl
title: phosphor-surface-packs' check.py does not compile GLSL or check the schema
repos: [phosphor-surface-packs, PlasmaZones]
domains: [shader, test]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`scripts/check.py` checks ids, files, includes and SPDX only. GLSL compilation (`plasmazones-shader-validate
--surface`) and the metadata schema gate (`scripts/validate-json-schemas.py`) run only in PlasmaZones, against the
commit it pins. Run both from a PlasmaZones build over the surface-packs checkout before a pull request that
changes GLSL or metadata.

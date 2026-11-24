<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones GLSL shader review notes

Read by `phosphor-works:shader-reviewer` in addition to its own instructions.

## Partition coverage

- Shader source (`.glsl`, `.frag`, `.vert`) in `plasmazones/data/overlays`, `plasmazones/data/animations`, `plasmazones/data/pointer`, the surface packs (`../phosphor-surface-packs/packs`), `../phosphor-libs/libs/phosphor-shaders`, and shader-pack metadata JSON.
- The KWin effect and the overlay, animation, surface and pointer shader packs. Whole shader themes also have `plasmazones:shader-art-director`, `plasmazones:shader-material-reviewer` and `plasmazones:shader-motion-reviewer`.
- Evidence example: "`migrateWindowTo` rewrites the live screen but carries the zone (SnapState.cpp:430-441)" is a finding. "The capture is stale because it never re-homes" is a hypothesis.

## The four shader families (do not mix their contracts)

- **Overlays** (`plasmazones/data/overlays/**`, per-zone visuals): the shared prologue from `plasmazones/data/overlays/shared/`. `common.glsl` is auto-prologued, plus `audio.glsl`, `depth.glsl`, `textures.glsl`, `wallpaper.glsl`, `multipass.glsl`, `flow-noise.glsl`, `logo-drift.glsl`, `zone.vert`.
- **Animations** (`plasmazones/data/animations/**`, window and desktop transitions): `animation_uniforms.glsl`, `easing.glsl`, `noise.glsl`, `audio.glsl`, `old_content.glsl`, `desktop_transition.glsl`, `anchor_remap.glsl`, `bmw_compat.glsl`, `strip_transition.glsl`, `animation.vert`.
- **Surface** (`../phosphor-surface-packs/packs/**` in phosphor-surface-packs, pinned by `cmake/PlasmaZonesDependencies.cmake`, decoration and backdrop chains): `surface_uniforms.glsl`, `surface_lib.glsl`, `surface_audio.glsl`, the blur, backdrop, color, noise and multipass helpers, `gaussian_h/v.frag`, the `kawase_down_*`/`kawase_up_*` blur passes, `surface.vert`.
- **Pointer** (`plasmazones/data/pointer/**`, cursor trails and click effects): `pointer_uniforms.glsl`, `pointer_lib.glsl`, `pointer_noise.glsl`, `pointer_multipass.glsl`, `pointer.vert`. The canvas is the whole output in device pixels. `reach` bounds the damage, and a `kTrailSeconds` constant must equal the metadata's `trailSeconds`.

## Contracts

- **Uniform contract = C++ assembly.** Every uniform a shader reads must be declared and provided by the daemon-side stage assembly (introspection-driven). A compile error is SWALLOWED at run time and renders flat gray, so any syntax risk, missing declaration or version mismatch is at least HIGH. The preview tool must mirror the daemon assembly.
- **Direction contract**: animation legs always run forward. Direction is encoded in `iFromRect`/`iToRect`, never by reversing time. A shader that infers direction from progress inversion is a finding. Desktop-switch shaders use `iSwitchDelta`. Maximize-class geometry shaders are skipped during user moves.
- **Easing misreads**: an inverted smoothstep (swapped edges, or `1.0 -` applied twice) reads as working in one leg and dead in the other. Check both legs. A full-catalog sweep already removed six packs' worth of dead uniform domains.
- **Alpha**: the compositor side no longer has `handlesOpacity`, so a shader must not apply again an opacity the C++ side already applied. Zone `activeOpacity` is the sole alpha source for overlay tint paths.
- **HDR and colour management**: final colour goes through the `PZ_FINALIZE_COLOR` hook. NEVER `sourceEncodingToNitsInDestinationColorspace` (it double-tonemaps).
- **Multipass**: buffer passes use the `builtin:` buffer token convention through the family's multipass helper. Surface chain fold caching is keyed on shader introspection (a PREFIX property), never on the pack id.
- **GPU cost**: the effect does multiple full-canvas draws per decorated window per frame.
- **Overlay scale contract (PR #841).** Every length an overlay pack expresses in logical px must reach device px through the shared helpers in `plasmazones/data/overlays/shared/common.glsl`: `zoneSdf()` for the corner radius, `zoneBorderWidth()` for the border, `zoneLen()` for every other length measured against a zone edge (glow reach, edge fade, travelling rings), `zoneStrokeWidth()` for a stroke derived by scaling the border down, and `zoneEdgeBand()` for an effect that only sits near the edge and must not die when the border is set to 0. A raw device-px constant beside one of those IS a finding, because the two then drift apart on a scaled display. `pxScale()` is 1080p-relative and answers a different question, so it belongs only to full-screen background patterns. Per-pack `max(radius, N)` corner floors are forbidden. `zoneFillColors[i].rgb` is PREMULTIPLIED by the zone's opacity, so a tint must go through `zoneFillHue()`. `zoneBorderColors[i]` is not premultiplied.

## Licensing homes

- LGPL-2.1-or-later: `../phosphor-libs/libs/phosphor-shaders/**`, the shared easing and noise helpers such as `plasmazones/data/animations/shared/easing.glsl`, and the PlasmaZones-original shaders in `plasmazones/data/animations/**` and `plasmazones/data/pointer/**`, so a third-party pack can build on them.
- GPL-3.0-or-later ONLY where upstream copyleft is incorporated: the Burn-My-Windows ports and their `shared/bmw_compat.glsl` shim, and the niri `honeycomb` port. These also carry a second `SPDX-FileCopyrightText` crediting the upstream author.
- `plasmazones/data/overlays/**` is currently GPL and has not been normalized, so follow the existing header there.
- The surface packs are mixed and carry their own REUSE licensing in phosphor-surface-packs.

## Known past-bug shapes (from prior audits)

- **GLES dialect on KWin 6.8.** KWin 6.8 compiles compositor stages as GLSL ES 3.00, and glslang accepts what Mesa and NVIDIA reject. What broke: `int` uniforms with no `precision highp int` under `#ifdef GL_ES` (both stages must agree), a late or unguarded `#extension` (guard it with `#ifndef GL_ES` and put it before declarations), an unguarded `layout(binding=N)`, and varying `layout(location)`.
- **Catalog contracts applied to part of the catalog.** Border alpha (eight packs did not fade the whole border by `borderColor.a`), fill alpha (four of 27 packs multiplied in `activeOpacity`), the zero-width border and the glow bounds were each fixed pack by pack and missed some. When a change touches a shared contract, grep every pack in the family, not only those in the diff.
- **Degenerate inputs to shared math.** `smoothstep` with equal edges (a border width of 0 through `softBorder`) and a polygon whose closing vertex repeats (a zero-length edge used as a divisor) gave NaN on exact fragments, and `clamp` need not absorb a NaN.
- **Exponential falloff cut at a bound.** Sixteen glow bounds gated an exponential while its value was still large and painted a hard ring. Subtract the value at the bound with `expGlowBounded()`.
- **Pointer packs outside their budget.** The host sizes damage from the pack's declared `reach` or `reachParam`, so anything drawn past it is cut on a straight edge (Sparks, Click Ripple, Orbit). Packs also decayed per frame against a wall-clock host, which left a frozen smear at 30 Hz, and gated on raw speed instead of the filtered `uPointerVelocity.w`.

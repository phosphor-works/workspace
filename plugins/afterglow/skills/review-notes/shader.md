<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Afterglow terminal shader review notes

Read by `phosphor-works:shader-reviewer` in addition to its own instructions.

## Partition coverage and hand-offs

- Covers `data/shaders/**` (the bundled Phosphor and neutral packs, each a `metadata.json` plus GLSL, and in `data/shaders/shared/` the flat event pack implementations, the rim and spectrum headers and the terminal contract headers) and every shader pack under `examples/**` (`shaders`, `glasshouse/shaders`, `phosphor/shaders`, `packages/*/shaders`).
- Afterglow packs are GLSL 4.50 baked to SPIR-V by QShaderBaker for Vulkan. A pack shades one canvas: a pane layer, a pane, the window, a buffer pass, the overview, the tab-switch or pane-effects pass over the window, or the overlay-transition pass over one pane.
- docs/SHADER-API.md and docs/SHADERS.md are the user contract. docs/WRITING.md governs metadata `name`/`description` and README prose.
- A contract header change must be checked against `libs/afterglow-render/include/AfterglowRender/ShaderProgram.h`, `PostChain.cpp`, every pack that includes it, and both docs.
- Do not run `afterglow_renderpng`. Name the render that would settle a visual claim (pack, `--param`, `--time`, `--overview-amount`, `--overlay-progress` and so on).

| Subject | Reviewer |
| --- | --- |
| The C++ side of the contract (`ShaderProgram.h` mirrors, PostChain bindings, budgets) | `afterglow:render-reviewer` |
| The app code that eases and feeds overview, transition, pane-effect and overlay-fade state | `afterglow:window-reviewer` |
| ShaderLibrary pack lookup and presets, the demos' `config/*.json` | `phosphor-works:config-reviewer` |
| Package manifests, `init.luau`, the pulse and suggests rules, the demos' `scripts/*.luau` | `phosphor-works:luau-reviewer` |
| README prose, REUSE.toml, ShaderControlsTest, the demos' README.md, PERFORMANCE.md, validation-results.json and preview.webp | `phosphor-works:build-reviewer` |
| The demos' `bin/*` | `afterglow:platform-reviewer` |

## Evidence and repeats

- Evidence example: "`paneTexel` clamps the card index and picks the source from `uPaneTab[i].y` (terminal_panes.glsl:97-104)" is a finding. "The cards sample the wrong tab" is a hypothesis.
- The colour helpers are defined by the contract (`terminal_color.glsl`). A pack copy of one is a compile error.
- Repeats to check: frame 0 after a buffer reset, a feedback buffer's second frame, `iTime` across its 1,024 s wrap, a highlight that has counted past the last card, and both ends of every progress.
- Next readers: the next pass's `iChannel`, the composite, the C++ field that mirrors the value.

## The contract (verify against the code, not memory)

- **Entry points**: final and buffer passes define `vec4 pTerminal(vec2 uv)`, which returns premultiplied encoded sRGB. `vertexShader` defines `vec4 pVertex(vec2 uv)`. Mesh passes define `vec4 pMesh()`. A final pass that moves content defines `vec2 pPointerMap(vec2 uv)`, which returns the coordinate that `pTerminal` samples (docs/SHADER-API.md "Pointer maps"). Only pane and window chains use it. Layer chains and event packs ignore it. The host prepends `#version 450` and `terminal_lib.glsl`. A stage that defines `main()` itself is taken as complete. `mainImage` and raw files no longer load.
- **Bindings**: 0 `TerminalUniforms` UBO, 1 `uTerminal`, 2–9 `iChannel0`–`7`, 10 `uAudioSpectrum`, 11–14 `uTexture0`–`3`, 16 `uDepthBuffer`, 17 `uPreviousText`, 18 `TerminalScene`, 19 `TerminalPanes`, 20 `uTabImage`, 21 `uTabAtlas`. 15 is Phosphor's wallpaper slot and is not bound. Only `iChannelResolution[0..3]` exist for eight channels.
- **Block sizes**: `TerminalUniforms` 5,200 bytes, `TerminalPanes` 2,656, `TerminalScene` 8,192, each mirrored by a `static_assert` in `ShaderProgram.h`. An offset comment, field or size changed in a header without its C++ mirror and docs is HIGH. A new header must join the `qt_add_resources` list in `libs/afterglow-render/CMakeLists.txt`.
- **Opt-in modules**: `terminal_multipass.glsl`, `terminal_audio.glsl` (turns on audio capture), `terminal_history.glsl` (allocates previous-text storage), `terminal_scene.glsl`, `terminal_panes.glsl`. Including one the pack does not use costs memory or capture. Using one without including it fails to compile.
- **Frames**: `animated()` is true when the pack's own text (comments stripped) names `iTime`, `iTimeDelta`, `iTimeHi`, `iFrame`, `iDate`, `timeAngle`, `timeCycle` or `timeSeconds`, when it includes `terminal_history.glsl`, when a scene object spins, or when a buffer pass has `feedback` or is animated itself (`ShaderProgram.cpp`, `compile`). Event ages are separate: `cursorAge`/`focusAge`/`uEventAges` and `signalAge`/`uSignal` render frames for `settleSeconds` after each event only. A pack that moves without one of these renders only when something else asks for a frame. Overview, tab-transition, pane-effect and overlay-transition packs run only while their state shows. The window times the overlay fade and asks for its frames.
- **Coordinates**: everything is top-down. Buffer passes see scaled pixels in `iResolution`, cursor and mouse. `uTerminalRect`, `uWindowSize` and `uWindowMouse` stay in window pixels. `iTime` wraps every 1,024 s, so read it through periodic functions or `iTimeHi`.
- **Metadata**: every `p_<id>` used is declared and every declared parameter is used. At most 32 scalars, 16 colours and 4 images. Ranges and defaults agree with how the code reads them. `windowBackground` works only in the background chain. Packaged packs must declare the id `<package>.<pack>`, where `<pack>` is the directory name (a `shared/` directory is skipped). A package holds 1 to 16 packs.
- **Licensing**: new packs in `data/shaders/**` and `libs/**` are LGPL-2.1-or-later (metadata through REUSE.toml). Feedback Glow, Depth Trails and Mesh Reactor are GPL-3.0-or-later. Example packs follow their existing headers (Glasshouse and Phosphor are GPL-3.0-or-later). Check sibling headers before flagging.
- **GPU cost**: overview and transition packs shade every window pixel each frame, at 4K, at display rate.

## Known past-bug shapes

- **Pane Deck cards flipped sides with two panes.** Offsets wrapped by the card count put the seam on a card. Wrap by the whole ring, keep the seam behind the highlight, and turn cards by `sin(angle)`.
- **The highlight position jumped back at the wrap.** `highlightPosition()` keeps counting past the last card. Check that every pack takes it modulo `paneCount()` and stays continuous.
- **Pane Deck cost +10 ms at 4K with 27 cards.** It shaded every card a ray crossed. Find the nearest two hits first, then shade only those.
- **Inverted `smoothstep` edges.** Glasshouse and Phosphor Field had `smoothstep(a, b, x)` with `a > b`. Write `1.0 - smoothstep(lo, hi, x)`.
- **A pack redefined a contract helper.** Phosphor Depths defined `srgbToLinear`/`linearToSrgb`, which `terminal_color.glsl` owns, and failed to compile. A failed pack only logs and drops out of its chain, so treat any compile risk as HIGH.
- **Mesh Reactor broke across split panes.** The camera used buffer-local coordinates. Scenes that span panes use `uTerminalRect`/`uWindowSize`, and window-wide backgrounds set `windowBackground`.
- **The leaving portal used the wrong colour uniform.** Check that every colour read names the documented uniform (`uThemeCursorColor` for the portal).
- **Overview and transitions must start and end exactly on the window.** At `overviewAmount()` 0 and at progress 0 and 1, the output must equal the flat input or `previousTabTexel`. Springs overshoot past 1, so check the math there too. An overlay transition must equal `overlayHostTexel(uv)` at progress 0 and the input at 1. Its progress is clamped to 0..1, and a fade stops at its end.

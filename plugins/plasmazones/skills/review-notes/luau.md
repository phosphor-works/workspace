<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones Luau tiling-algorithm review notes

Read by `phosphor-works:luau-reviewer` in addition to its own instructions.

## Partition coverage

- `plasmazones/data/algorithms/*.luau` and the Luau-facing glue in `../phosphor-engine-libs/libs/phosphor-tiles` and `../phosphor-libs/libs/phosphor-scripting`. Algorithms are scripted through phosphor-tiles.
- Verify a pluau helper you flag against its definition in phosphor-tiles, and check every algorithm that uses it.
- Evidence example: "`migrateWindowTo` rewrites the live screen but carries the zone (SnapState.cpp:430-441)" is a finding. "The capture is stale because it never re-homes" is a hypothesis.

## The pluau contract

- Every algorithm is `return pluau.algorithm { metadata = {...}, tile = function(ctx) ... end }`, plus optional resize and memory hooks. The metadata block is a machine-read contract, not documentation.
- `supportsSplitRatio`, `supportsMasterCount`, `supportsMemory`, `producesOverlappingZones`, `minimumWindows`, `defaultMaxWindows` and `zoneNumberDisplay` must each MATCH what `tile()` does. A `tile()` that reads `ctx.splitRatio` while `supportsSplitRatio = false` (or the reverse), or returns overlapping rects with `producesOverlappingZones = false`, is a HIGH finding. The daemon gates UI and behavior on these flags.
- `id` should match the filename. `name` and `description` are user-facing and follow the prose rules.
- **Use the pluau helper library, do not reimplement it.** The stdlib includes `guardArea`, `clamp`/`clampSplitRatio`, `rect`/`fillArea`/`fillRegion`, `distributeEvenly`/`distributeWithOptionalMins`, `dwindleLayout`/`masterStackLayout`/`deckLayout`/`stripLayout`/`gridShape`, the min-size machinery (`applyPerWindowMinSize`, `computeCumulativeMinDims`, `minSizeAt`), and `appendGracefulDegradation`. Hand-rolled duplicates of these are DRY findings. A helper that exists but is bypassed for one branch is a consistency finding.
- **Standard early-out**: `local early = pluau.guardArea(area, count); if early then return early end` before layout math. A missing guard is a degenerate-area crash risk.
- **Geometry**: `ctx.area` is the work area in pixels, and `tile()` returns integer pixel rects `{x, y, width, height}` inside it (`variantToRects` in `luautilealgorithm.cpp` reads them with `toInt()`). They are not relative 0.0 to 1.0. That convention is for persisted layout JSON. Fractional math must round so the zones still tile the area. Check gap handling (`ctx.innerGap`), min-size propagation (`ctx.minSizes`), and that the sums of splits tile the area (no drift from repeated subtraction, no zone past the area).

## Layout math and edge cases

- Window counts 0, 1, exactly `minimumWindows`, and above `defaultMaxWindows`. Split ratios at and beyond the clamp bounds. Areas smaller than the cumulative minimum sizes, where the graceful degradation path must engage and not produce negative-size rects.
- Zero-size or negative rects in the return value are CRITICAL. The engine consumes them directly.
- **Determinism**: `tile(ctx)` must be a pure function of `ctx` unless `supportsMemory = true`, and then state goes through the sanctioned memory mechanism only. Module-level mutable state is a finding, because algorithms run again on each relayout and are shared across screens. (Afterglow scripts may keep module-level state, which survives a reload only while the source is unchanged. The two contracts differ by design.)
- Overlapping-zone algorithms interact with directional-move tie-breaking: the gap clamp can tie candidates at 0 and pick the farthest zone. Flag layouts that produce coincident edges without considering this.

## Licensing

- `plasmazones/data/algorithms/**` is GPL-3.0-or-later. Luau inside `../phosphor-libs/libs/phosphor-*` follows the library (LGPL-2.1-or-later).

## Known past-bug shapes (from prior audits)

- **Host work outside the protected call.** `Marshal::toVariant` runs after `guardedPcall` returns, outside the watchdog and the heap cap, and needed four separate bounds: self-referencing tables and shared-subtable fan-out (`MaxNodes`), one large string referenced many times (`MaxBytes`), and deep nesting (`lua_checkstack`). An over-budget result must be `CallStatus::Error`, never an empty value read as nil. The heap cap is enforced inside `guardedPcall` only. Any new host-side walk of script data needs the same bounds.
- **Script output reaching geometry unchecked.** A non-finite override passed through `std::clamp` as NaN (`resolveReal`), a zone count disagreed with the window count, a custom-param range came back inverted, and `cascade.luau` divided by an unguarded `count - 1`. Validate every value a script returns before layout math (`clampZonesToArea`), and guard divisors in `.luau` even where the host short-circuits the case.
- **Algorithm id collisions.** The loader registers by metadata id, the first registration wins, and the user directory scans first. Create and import once probed only the user directory, so a new "Grid" unregistered the bundled one, and a user script could replace a C++ built-in. `ScriptedAlgorithmLoader` now refuses a built-in collision, and `AlgorithmRegistry` reserves `none` and the `autotile:` prefix. A new writer must probe the whole data search path.
- **Script state crossing algorithms.** `ctx.state` belongs to one algorithm. `supportsScriptState` gates both the read and the `onWindowResized` write-back in `LuauTileAlgorithm`, and the engine drops stashed bags on an algorithm switch or an override change (`dropStashedScriptStatesForAlgorithmChange`). A metadata flag that is parsed but never read is a finding.
- **Hand-scanning Luau source.** `plasmazones/src/settings/services/algorithmscaffold.cpp` rewrites metadata by tracking brace depth. An unclosed long bracket, and then a backtick string holding `}`, each desynced it into emitting duplicate `name`/`id` keys. A scanner must know all three string forms and reject rather than corrupt.

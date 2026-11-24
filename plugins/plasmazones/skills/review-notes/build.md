<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones build, test and data review notes

Read by `phosphor-works:build-reviewer` in addition to its own instructions.

## Partition coverage and hand-offs

- Covers the CMakeLists.txt files, `plasmazones/tests/`, the `plasmazones/data/` JSON assets (layouts, `whatsnew.json`), translations, `CHANGELOG.md`, docs and packaging.
- Luau algorithm sources and their metadata prose go to `phosphor-works:luau-reviewer`. Shader sources and pack metadata go to `phosphor-works:shader-reviewer`.
- Evidence example: "`migrateWindowTo` rewrites the live screen but carries the zone (SnapState.cpp:430-441)" is a finding. "The capture is stale because it never re-homes" is a hypothesis.

## Build

- `qt_add_qml_module()` uses the versionless spelling in this repo.
- `USE_KDE_FRAMEWORKS=ON` and `OFF` must both stay buildable. KF6-only code (`KCMUtils`, `GlobalAccel`, the optional `Activities`) needs guards. The pluggable backends (`PhosphorConfig::IBackend`, `PhosphorShortcuts::IBackend`, `IWallpaperProvider`) keep the portable build honest.
- `cmake/PlasmaZonesDependencies.cmake` is the only place the pins live: phosphor-libs, phosphor-engine-libs, phosphor-components, the branding release and phosphor-surface-packs. `scripts/check-conventions.py` (the dep-pins rule) fails when a packaging recipe no longer matches a pin.
- `find_package` ordering and visibility for the phosphor-* libraries has bitten before. Verify that new targets link what they include.
- Never suggest `cmake --install` or `sudo` steps. The user installs. (This source rule is stricter than the shared reviewer, which allows an install into a temporary prefix to check the layout.)

## Tests

- Qt Test: `QTEST_MAIN`, `QCOMPARE`/`QVERIFY`. Mock D-Bus for daemon tests. Cover empty zones, overlapping zones and invalid coordinates.
- ctest MUST run under the D-Bus isolation setup: `TEST_LAUNCHER` is `dbus-run-session` with a no-servicedir conf. A test that reaches the stock session bus can activate the installed daemon and hang ctest through the stdout pipe. Every new test target must inherit the launcher.
- Licensing: top-level `plasmazones/tests/**` is GPL-3.0-or-later. `../phosphor-libs/libs/phosphor-*/tests/**` follow their library (LGPL-2.1-or-later).

## Data and prose

- Text that users see in `plasmazones/data/**/*.json` (`description`/`name`), `plasmazones/data/whatsnew.json` and `CHANGELOG.md` follows the prose rules.
- `CHANGELOG.md`: Keep-a-Changelog structure, with a version compare link for every version.
- Layout JSON uses relative geometry (0.0 to 1.0) and zone QUuids. Validate that new data files parse against what the loaders expect.

## Known past-bug shapes (from prior audits)

- **Tests that cannot fail.** `(compositor)` matched `OK (compositor GLES)`, a substring exclusion that a sibling arm satisfied (a HIGH in PR #1143). The other recorded forms are in the shared reviewer's list.
- **Fixture teardown order.** Four sites in `test_wta_capture_guards.cpp` declared a `std::unique_ptr` after the `QObject` parent it was wired to.
- **Nested-KWin probes that cannot fail.** Under `scripts/nested-kwin/regression/`: greps for text the log never contains, checks that read only post-restart logs, `stage_fail` inside `$( )` running cleanup in a subshell while the probe carried on, ignored `setSetting` results (use `gsetting_ok`), and staging gates that accepted "not floating" as "tiled". Each check needs a baseline it fails on.
- **CHANGELOG claims and conflicts.** Entries overclaimed against the code (behaviour that sibling findings left open, a scope wider or narrower than the diff). `[Unreleased]` conflicted with main in three audited PRs. Check each sentence against the code, and merge main before closing.
- **Catalog drift.** New `i18n()`/`tr()` strings shipped without `update-ts`. The pt_BR action labels and tooltips mixed third-person forms (`Adiciona`, `Define`, `Exclui`) with the infinitive over many rounds. A fix to one string sweeps its siblings in the same catalog.
- **Build graph out of step with the links.** The installed `PhosphorTilesConfig.cmake.in` lacked the `find_dependency` for a new PUBLIC link. A test linked a target that exists only under an optional build flag, which broke the documented configure, so no test built. Gate optional links on `TARGET`, and update the Config file with the link set.

<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones notes for phosphor-works:qml-reviewer

PlasmaZones QML runs on Qt6, KF6 and Kirigami, Wayland-only. Apply these notes in addition to the shared reviewer's checks.

## Scope and hand-offs in PlasmaZones
- The QML reviewer covers .qml files and the QML-facing controller layer in `plasmazones/src/settings`, `plasmazones/src/editor`, `plasmazones/kcm`, and the QML shipped by tier-1 libraries under `../phosphor-libs/libs/*/qml` and `../phosphor-engine-libs/libs/*/qml` (phosphor-surface-quick's `SurfaceDecoration.qml`, phosphor-control's `qml/` and phosphor-engine-runtime's overlay `qml/`).
- For `plasmazones/src/settings` this means the QML property-bridge surface. The Settings, ConfigDefaults and persistence C++ belongs to `phosphor-works:config-reviewer`.
- The editor-side `ILayoutService`, `ZoneManager` and `SnappingService` in `plasmazones/src/editor` are reviewed here.

## i18n pipeline
- QML uses `i18n()`/`i18nc()` (via PhosphorLocalizedContext). QML is NOT handed to lupdate directly. `update-ts` runs `scripts/qml-i18n-stubs.py` first, which transcribes each `i18n()` call into a C++ stub lupdate does understand, and feeds those stubs to lupdate instead (`cmake/PhosphorTranslations.cmake:87-92,120-151`).
- So QML `i18n()` strings DO reach `plasmazones/translations/*.ts`: the great majority of the i18n-family sources under `plasmazones/src/**/*.qml` are present in the German catalog today.
- `-no-obsolete` means a scrape gap deletes live translations from all seven catalogs in one run.
- `plasmazones/kcm` uses `qsTr()` and goes to lupdate raw (as does `../phosphor-libs/libs/phosphor-control/qml`).

## PlasmaZones invariants
- Zone identity: zone IDs (QUuid) in QML too, never indices.
- A bare dialog `Loader` inside `ExpandableRowDelegate` eats a spacing slot; wrap in `Item { visible: false }`.
- A component instantiating its own settings object shadows the context `ISettings`, so writes silently no-op — check where page state derives from combos.
- Translucency in KWin-side items goes through `Item::setOpacity`, not QColor alpha (the prior scene-graph OutlinedBorderItem ignored QColor alpha; it is superseded by server-side decoration, but the rule stands); zone `activeOpacity` is the sole alpha source and colour alphas must be stripped in Rectangle paths.

## Known past-bug shapes to check for (from prior audits)
- **Fixed-geometry zones on relative-only paths.** Undo, redo, cancel and paste replayed relative rects through `ZoneManager::updateZoneGeometry`/`updateZoneGeometryDirect`, which take pixels for a fixed zone, and collapsed it to 50x50 at the origin (`FillZoneCommand`, `DividerResizeCommand`, multi-select cancel, the clipboard in `ZoneSerialization`). A new zone-geometry path carries the zone's geometry mode and fixed rect.
- **Undo that recomputes instead of restoring.** `UpdateZoneAppearanceCommand` re-seeded theme colors when `useCustomColors` flipped, and the unit-toggle bounds override recomputed from current state.
- **Screen facts cached at switch time.** Editor scale, usable-area insets and virtual-screen geometry were read once per screen switch (`ensureTargetScreenScale`, `refreshUsableAreaInsets`, `targetLogicalScreenSize`) with no subscription, so a scale, panel or VS change left them stale, and an unreachable daemon left the scale at 1.0 silently.
- **Blocking D-Bus on the GUI thread.** Sync round trips per screen switch, per model READ and per local reload (`SettingsController::recalcLocalLayouts`, the editor's `screenModel`) recurred in both apps. Prefer async, or a cached value refreshed on the daemon's change signal.
- **Paths that replace the loaded document.** `importLayout` skipped the unsaved-changes check its siblings apply, the load fast path read a registry snapshot older than the save just confirmed, a parked screen switch outlived its layout, and dialogs stayed open across a mode change. Every path that swaps the layout or template goes through the same gate and reset.
- **Re-sync handlers that sever bindings.** `onXChanged` handlers and `Connections` blocks pushing a stored value back into `SettingsSlider.value`, `checked` or `keySequence` severed the binding (a HIGH in PR #1172).
- **Control bounds copied as literals.** Slider from/to written in QML drifted from `ConfigDefaults` (0.5 against a schema max of 1.0, 1-50 against 1-100). Bounds come from a controller `CONSTANT` facade (`SnappingZonesController`, `EditorPageController`).
- **Case-sensitive id compares.** Zone and layout id compares in the rule pickers were exact while the rule engine's Equals ignores case, so a hand-edited id showed as dangling. Condition values compare through `qml/js/MatchWireValue.js`.

<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# PlasmaZones configuration and settings review notes

Read by `phosphor-works:config-reviewer` in addition to its own instructions.

## Partition coverage

- The engine runtime's settings model (phosphor-engine-libs' `libs/phosphor-engine-runtime`, `src/config` and its public headers), `plasmazones/src/common/hostsettings`, the `plasmazones/src/settings` C++ (controllers, Settings, ConfigDefaults, migrations), phosphor-config, phosphor-shortcuts, and the rules and profile plumbing.
- The Settings section of the project `CLAUDE.md` is the authority.
- Evidence example: "`migrateWindowTo` rewrites the live screen but carries the zone (SnapState.cpp:430-441)" is a finding. "The capture is stale because it never re-homes" is a hypothesis.

## Architecture invariants

- **Chain**: `ISettings` interface → `Settings` class → `PhosphorConfig::Store` over a pluggable `PhosphorConfig::IBackend` (default `JsonBackend` at `~/.config/phosphor-works/plasmazones/config.json`). Defaults live ONLY in `ConfigDefaults`. The old `.kcfg` schema files were removed from the repo, so a `.kcfg` that comes back is itself a finding.
- **Adding a setting requires all six touchpoints**, in the store-backed shape. A partial wiring is a finding.
  1. `configdefaults_<area>.h`: the static default accessor, plus a `constexpr` Min/Max for a clamped numeric.
  2. `configkeys.h`, or `configkeys_scrolling.h` for a scrolling group and `configkeys_workspaces.h` for a workspaces group: the group and key accessors, if new. Not `configdefaults.h`, which declares none. The call is still spelled `ConfigDefaults::` through inheritance. The `P_CONFIG_*` macros come from `configkeymacro.h`.
  3. `settingsschema*.cpp`: the `{key, default, QMetaType, description, coercion}` KeyDef. The store takes its default, type and clamping from here, not from the getter.
  4. `plasmazones/src/core/interfaces/isettings.h`: the ISettings signal.
  5. `plasmazones/src/config/settings.h`: Q_PROPERTY, getter and setter, with **no member variable**.
  6. The matching `plasmazones/src/config/settings/*.cpp`: the store-backed getter and setter. There is **no** load, save or reset arm. Persistence goes through the store.
- A clamped setter must write first and compare after, because the schema's coercion runs on the write.
- **Key strings**: every config group or key string goes through a `ConfigDefaults::` accessor. Any inline `QStringLiteral("Some.Group")` for a config key is a finding. v2 groups are dot-paths that mirror the UI hierarchy. Key accessors are generic and disambiguated by group.
- **No ad-hoc backwards compatibility** (the most-violated rule): no per-key migration for renames within a schema version, no fallback reads from legacy groups, no writing empty strings to clear obsolete keys. Old values are silently dropped by design.
- **Whole-schema migrations are the ONE exception** (`migrateVnToVn+1`). Each is in its own `configmigration_v<N>.cpp`, with the `MigrationStep` registry in `configmigration.cpp`: exactly one function and one `MigrationStep` per version bump, transforming the whole JSON root and stamping `_version`. The `v1*` accessors in `configkeys.h` exist only for migration readability. If a release branch already bumped the schema version, batch further fold-ins into THAT unshipped migration rather than adding another bump.
- **Shortcuts** route through `PhosphorShortcuts::IBackend` via `ShortcutManager`.
- **Per-page reset and discard**: a baseline snapshot, the `pageOwnedConfigKeys` manifest and a value-based dirty check. A page's reset must touch only its own subtree. Shared-blob domains wiped siblings before, so check any new page wiring.
- **Editor settings are separate** (EditorController, a separate process). Daemon settings that leak into the editor path, or the reverse, are an architecture finding.
- **Profiles**: config and rules delta and inheritance with a staged apply. Mutations must go through the staging path, not direct backend writes.
- **Qt and licensing**: `QLatin1String` for JSON keys, `PhosphorI18n::tr()` in C++, QUuid with braces except in filesystem paths, GPL for `plasmazones/src/**`, LGPL for the phosphor libraries.

## Contradiction with Afterglow

PlasmaZones is released and allows whole-schema migrations (above). Afterglow is unreleased and allows no migration code at all. Apply the rule of the repo under review.

## Known past-bug shapes (from prior audits)

- **Bulk paths that skip per-key signals.** `discardKeys`, `resetKeys`, `applyConfigOverlayStaged` and `reset()` re-emitted only Q_PROPERTY keys. So Editor.* and the animation profile never announced a discard, reset or staged profile: `editorSettingEntries()` was read only by `load()`, and two arms lacked `emitAnimationProfileChangeIfMoved`. A bulk mutation reaches the same signals the setter emits. An Editor.* key needs rows in `editorSettingEntries()` and `EditorOwnedConfig`, and announces on `editorSettingsChanged`.
- **Whole-file writes from a stale or stand-in document.** `Settings::save()` and the editor flush rewrite the whole root. A store loaded before another process wrote, or the `{}` that a failed parse leaves, clobbered or wiped `config.json` (a HIGH in PR #1172). Check that writes go through `JsonBackend`'s `loadFailed()`/`lastGoodRoot` refusal and `Settings::reloadPreservingLocalEdits`, and that members read from a stand-in never overwrite a repaired file.
- **External changes dropped while busy.** A `settingsChanged` that arrived during a settings-app save (`m_saving`) or while the editor's save timer ran was discarded instead of deferred. A refused write was not retried once the file read cleanly. Follow every early return in a reload handler to where the skipped change is replayed.
- **Corrupt-file handling belongs to the daemon.** Only the daemon quarantines an unreadable config (`ConfigMigration::CorruptConfigHandling::Quarantine`). The editor and the settings app use `LeaveInPlace`. Launch-time migration in a non-daemon process, D-Bus activation order and guessed `.corrupt.bak` paths each broke this in one audit.
- **Default-pruned persistence compared against the wrong default.** Per-algorithm slots were written at the global default, pruned at the algorithm's own default, or lost when the write filter and the read fallback disagreed. Raw writes stamped default-equal values, and a 0..1 slider stored 0.7000000000000001, so the exact compare never pruned. The write filter, the read fallback and the prune must use one default (the per-algorithm entries in `settingsschema_tiling.cpp`), with fractions rounded before the compare.

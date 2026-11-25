<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Afterglow configuration review notes

Read by `phosphor-works:config-reviewer` in addition to its own instructions.

## Partition coverage and hand-offs

- Covers `afterglow/src/config/**` (Settings and SettingsStore over PhosphorConfig, with the Mcp group that `afterglow mcp` reads at its start, Keybinds, KeyModes, Theme), `afterglow/src/shaders/**` (the ShaderLibrary pack registry, presets and package shader directories, and ShaderControls live parameter overrides), `data/themes/**`, the `config/*.json` settings and colours of the `examples/glasshouse` and `examples/phosphor` demos, and the generated docs/CONFIGURATION.md.
- `Settings.cpp` is about 2,600 lines. Read it in chunks.
- Readers to check for a renamed key, a new field or a changed default: `TerminalWindow`, `Pane`, `Application`, `ControlSocket`, `Control`, tests and docs.
- docs/WRITING.md governs every schema description.

| Subject | Reviewer |
| --- | --- |
| GLSL sources and `metadata.json` of every pack (bundled, example or package) | `phosphor-works:shader-reviewer` |
| The package manifest rules that hand shader directories over | `phosphor-works:luau-reviewer` |
| `TerminalWindow::applySettings` and how actions run | `afterglow:window-reviewer` |
| Application, ControlSocket, CommandSocket, `afterglow mux` (Mux.cpp, which sends settings to a session) and `afterglow mcp` (`afterglow/src/mcp/**`) as settings consumers | `afterglow:platform-reviewer` |
| The renderer's ShaderProgram and PostChain | `afterglow:render-reviewer` |
| ConfigTest and ShaderControlsTest as test code, CMake, REUSE annotations, the prose of other docs | `phosphor-works:build-reviewer` |
| Terminal core | `afterglow:vt-reviewer` |

## Evidence and shared state

- Evidence example: "`findPack` answers a package pack only to `<package>.<pack>` (ShaderLibrary.cpp:368-380)" is a finding. "The preset is lost after reload" is a hypothesis.
- Calls with wide effects: `SettingsStore::write` commits through the backend and then reloads. `setPackageShaders` rebuilds the registry and drops every cached program. `ShaderControls::rebuild` retires every override.
- Repeats: the file watcher, the desktop colour-scheme signal, `afterglow -o` overlays and `write()` all funnel into `reload()`. Follow the second reload, the reload after a parse error and the reload after the theme file is deleted and recreated.
- Next readers: `changed(previous)` consumers, `watch()`, the program cache, `m_failed`.

## Stack facts

- **One schema** (`buildSchema()` in `Settings.cpp`). Groups: `Font`, `Colors`, `Terminal`, `Window`, `Mouse`, `Links`, `QuickTerminal`, `Mux`, `Mcp`, `Control`, `Scripts`, `Audio`, `Animation`, `Graphics`, `Notifications`, `Shaders`, `Hints`, `Keybinds`. Keys use `intKey`/`doubleKey` (clamping), `enumKey` (an unknown value falls back to the default), `colorKey`, `curveKey` and `stringKey`, or a raw `KeyDef` (booleans, lists, maps). `SettingsStore::read()` maps each key into the `Settings` structs, and `reference()` feeds `--config-reference`. A key in the schema but not in `read()`, or the reverse, is a finding.
- **One source of defaults**: the struct initializers in `Settings.h` (`padding = 6`, `splitCurve = "spring:22,1"`). The schema passes `d.<field>` and never repeats a literal. The exceptions are `KeyModes::Default*Timeout`, `Keybinds::defaultMap()`, `defaultPalette()`, and empty strings, lists and maps. A literal default in the schema is a finding.
- **`reference()` derives ranges** by passing ±extremes through the validator. A validator that is not a plain clamp prints wrong ranges in docs/CONFIGURATION.md.
- **docs/CONFIGURATION.md is generated**: `python3 tools/generate-reference.py build/afterglow/afterglow`. A hand edit, or a schema change without regeneration, is a finding.
- **Unreleased product**: no migration code, no fallback reads of renamed keys, no compatibility aliases. A renamed key is renamed everywhere at once. (This contradicts PlasmaZones, which allows whole-schema migrations. Apply the rule of the repo under review.)
- **Reload**: `SettingsStore` watches the config file and every theme candidate (each search dir × `.json`, `.conf`, bare) through `PhosphorFsLoader::WatchedFileSet`, plus `QStyleHints::colorSchemeChanged` for `light:a,dark:b`. A file that fails to parse keeps the current settings. `afterglow -o` overrides are a `JsonBackend` overlay and must never reach the file. A missing file means every default. The file holds only the values that differ (sparse), and `write()` creates it private. A write that cannot be saved is rolled back in memory. `changed(previous)` is sent only when the settings differ, and consumers diff against `previous` before they do expensive work.
- **Themes**: the search order is the user's `~/.config/phosphor-works/afterglow/themes`, then the system dirs, then the bundled `data/themes`. A theme's colours replace explicit `Colors` keys. A missing divider is derived. Formats: Afterglow JSON, Ghostty and kitty.
- **Keybinds**: the `Action` enum plus the `Actions[]` table (token, title, defaults). `isStructural` feeds the script budget. Targets may be `script:<id>.<command>`, `text:<escapes>`, `table:<name>` or `pop_key_table`. `KeyModes` clamps the sequence timeout (100 to 10,000 ms) and the table timeout (100 to 60,000 ms) and rejects ambiguous prefixes. Text escapes must be UTF-16 surrogate-aware.
- **ShaderLibrary**: the base dirs are bundled, system (reversed `locateAll`), then `~/.config/phosphor-works/afterglow/shaders`. Package dirs follow. `ShaderRegistry` cannot drop a search path, so `buildRegistry()` makes a new one when packages change. `findPack` resolves a package pack only by `<package>.<pack>` (`packagedRef`), and other packs by directory name, the registry's UUID id or display name. Programs cache on the ref plus compact JSON overrides. Failures cache in `m_failed`. `m_dependencies` includes missing files, so watches can recover.
- **ShaderControls**: GUI thread only. Overrides are owner-scoped (`clearOwner` on script cleanup), the last write wins per parameter, and `rebuild` invalidates every instance ID. Transitions use Phosphor curve specs.
- **Qt and licensing**: the targets build with `QT_NO_CAST_FROM_ASCII` (`QStringLiteral`/`QLatin1String`). Signals use `Q_EMIT`. `afterglow/src/**` is GPL-3.0-or-later.

## Known past-bug shapes

- `Keybinds::unescape` converted each UTF-16 unit to UTF-8 alone, so emoji and `😀` pairs broke. Check every per-`QChar` encode loop for surrogate pairs.
- The theme watch was lost when an editor replaced or deleted the file, and watches piled up. `watch()` must run again on every reload and cover missing candidates.
- Overrides were merged into a predictable temp file at a PID path. Overrides stay in memory. Any config temp file is private and atomic (`QSaveFile`).
- A failed first shader load was cached in `m_failed` with no watch, so fixing the file never recovered. Record dependencies before any early `fail()`.
- Package packs registered under a UUID derived from their id, so lookups by `<package>.<pack>` failed until `packagedRef` matching. Test both id spellings in every lookup path (`load`, `presets`, `parameters`, `packIds`).
- docs/CONFIGURATION.md lacked `Terminal.bidi` and `Scripts.allowReadText` after schema changes. Diff the schema keys against the generated tables.
- `Settings.h` comments described the wrong contract or sat on the wrong declaration. Check each doc comment against its own field.
- An example config set colours while its base kept `Colors.theme`, so the theme won. Explicit colours need an empty `theme`.

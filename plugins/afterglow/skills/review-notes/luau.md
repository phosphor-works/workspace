<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Afterglow Luau scripting review notes

Read by `phosphor-works:luau-reviewer` in addition to its own instructions.

## Partition coverage and hand-offs

- Covers `afterglow/src/scripting/**` (ScriptHost, ScriptControl, ScriptPackage, ScriptState, ScriptTasks, `ScriptFiles.h`, the prelude `afterglow.luau` and the declarations `afterglow.d.luau`), `examples/scripts/**`, the `scripts/*.luau` of the `examples/glasshouse` and `examples/phosphor` demos, the Luau, `package.json` and README files of `examples/packages/**`, and docs/SCRIPTING.md and docs/PACKAGES.md as the user contract.
- Scripts are local and trusted to run, but a broken or looping script must never hang the GUI, trap the keyboard or reach past its effect budget.
- `ScriptHost.cpp` is over 1,700 lines. Read it in chunks.
- An effect kind lives in five places (the prelude, `afterglow.d.luau`, `Kinds[]` in `ScriptHost.cpp`, `ScriptControl.cpp`, docs) plus `Control`. Check them all.

| Subject | Reviewer |
| --- | --- |
| GLSL and `metadata.json` of package shader packs | `phosphor-works:shader-reviewer` |
| ShaderLibrary package registration, Settings and Keybinds | `phosphor-works:config-reviewer` |
| Control and CommandSocket (`afterglow/src/control`), the mux daemon (`mux/**`, and the window's side of a session in `afterglow/src/mux/**`), `aglow run` (`tools/aglow` and `libs/afterglow-proto/src/Run.cpp`), Application wiring and D-Bus | `afterglow:platform-reviewer` |
| `TerminalWindowScript.cpp` and the window side of key modes, dialogs and the overview | `afterglow:window-reviewer` |
| ScriptHostTest and ScriptPackageTest as test code, CMake, REUSE and doc prose style | `phosphor-works:build-reviewer` |
| Terminal core | `afterglow:vt-reviewer` |
| Renderer | `afterglow:render-reviewer` |

## Evidence and shared state

- Evidence example: "`queueResult` sends `afterglow.await:` IDs to `__resume` under the waiting handler's time limit (read in `ScriptHost::queueResult`)" is a finding. "The resumed handler sees the wrong pane" is a hypothesis.
- Calls with wide effects: `retire()` runs `on_unload`, clears tasks and calls `cleanup`. `call()` calls `failed` on every error and disables the script after five in a row.
- Repeats: handlers re-enter through timers, `watch_file`, results, `__resume` after every await, and the reload that `WatchedDirectorySet` triggers on each save. Follow the second resume, the next timer tick and the reload that keeps an unchanged instance.
- Next readers: the next `applyEffect`, `queueResult`, `emitOwned`, the prelude's `flows` table.

## Stack facts

- **Execution model**: every script has its own `LuauEngine` (16 MiB heap) and a shared `LuauWatchdog`. All Luau runs on the GUI thread, synchronously: 20 ms for events and a loose script's `on_load`, and 100 ms for each part of a command handler between waits and for a package's `migrate` and `on_load` (`EventTimeoutMs` and `CommandCallTimeoutMs`, both in `ScriptHost.h`). The prelude runs, then `engine->sandbox()`. Scripts have no `io`/`os` and reach the system only by returning effects. Five failures in a row disable a script until its file changes.
- **Await runtime** (`afterglow.luau`): `load()` wraps every module as `afterglow.__wrap((function(...) <source> end)(...))` on one line, so error lines stay correct. `wrap` returns a proxy whose function fields run as coroutines through `drive`. `migrate` and `on_unload` stay direct. Waits yield a private `Yield` sentinel, tag effects `afterglow.await:<flow>:<index>`, and the host routes those results to the `__resume` field.
- **Await limits**: `MaxWaiting` 16 handlers per script, `MaxBatch` 16 effects per `await_all` and `MaxOutstanding` 48 effects waited for at once per script in the prelude (below the host's 128 pending results, so waits alone cannot disable a script). `MaxSleeping` 16 and `MaxSleepMs` 600,000 in `ScriptHost.h`. Over the limit a wait resumes at once with code `busy`. `sleep` is refused unless awaited. Check that a forged or duplicate await ID cannot resume a flow twice.
- **Effect validation** (`ScriptHost::applyEffect`): `Kinds[]` declares each kind's pane, structural, string, command and number fields. The effect is rebuilt from those fields only, so a field the prelude sends but `Kinds[]` does not list is silently dropped. Kind-specific checks sit in two blocks. Any `error` set before dispatch must never reach a callback.
- **Budgets**: 64 effects per returned list, 20 per second, 60 `dock` effects per second on a budget of their own, 3 structural per 10 s, 128 queued and 128 delivered results per second (more than the two effect budgets together, `static_assert`ed), 64 owned callbacks per second. Result overflow disables the script, because refused requests retried from `on_result` would loop.
- **Routing**: `state_*`, `sleep`, `log`, `set_commands`, `output`, `output_error` and `exit` stay in ScriptHost. `timer`, `cancel`, `exec`, `read_file` and `watch_file` go to `ScriptTasks`. The rest go to `Callbacks::applyOwned` (`ScriptControl.cpp`), which owns shaders, dialogs, key modes, status and overrides by owner and passes everything else to `apply`. An unrouted kind reaches `"unknown effect"` at run time with no compile error.
- **Owners**: `owner` is `"<id>@<n>"`, unique per loaded instance. Owner-scoped state (key modes, dialogs, overrides, shader overrides, tasks) is freed by `cleanup` on retire. A key mode also ends through `failed` on ANY handler error, not only on disable. `on_key` reaches the holder only through `dispatchTo(owner, ...)`, so a replacement never inherits keys. Results and sleeps re-enter through `QTimer::singleShot(0)` with a `weak_ptr`. Never re-enter a VM synchronously.
- **ScriptTasks**: `exec` uses `QProcess` in a new session and SIGKILLs the process group on finish, timeout or clear. `read_file` runs on `QtConcurrent` with an atomic cancel flag and a global limit of 8 reads. Limits: 16 tasks per script, 128 total, a timeout up to 600,000 ms, `max_bytes` up to 1 MiB, timers 1 ms to 1 h with repeats of 0 or at least 250 ms.
- **Packages** (`ScriptPackage::read`): `package.json` needs `id` equal to the directory name, `version` x.y.z, `api_version` 1, `entry` and `modules`. Optional: `commands` (see Commands), `dependencies` (exact versions, 16 packages), `state_version` 1 to 10,000, `config` merged with `config.json`, `assets` (32 files, 4 MiB each, 16 MiB total), `shaders` (`path`, 1 to 16 packs whose `metadata.json` declares `<package>.<pack>`, `suggests` limited to the nine `Shaders` keys), `pulses` (32 names mapped to 4 to 255). Package files read total at most 1 MiB, a module 256 KiB, 64 modules. Every path stays under the canonical root, checked again on the opened fd. The entry's `metadata.id` must match the manifest.
- **Commands**: a package's `commands` map, a loose script's `metadata.commands` and `afterglow.set_commands` take the same map of name to `summary`, `usage`, `palette` and `stdin`, checked by `ScriptPackage`'s `readCommands`. Script IDs and command names never start with `-`, which `aglow run` would read as an option. A run starts from the palette, the context menu, a key, `afterglow ctl action script:ID.COMMAND` or `aglow run` through the `commands` target (`CommandSocket`). `ScriptHost::startCommand` calls the prelude's `__command`, which runs the script's `run_command(command, ev)` with `ev.args`, `ev.stdin` and the pane. `output`, `output_error` and `exit` reach the client. An awaited output resolves when the client has it, or with `cancelled` when the run has ended.
- **Command limits**: `Scripts.commandTimeout`, `Scripts.commandRunLimit`, and `Scripts.commandStdinLimit` and `Scripts.commandOutputLimit` in KiB (the Settings fields and `CommandLimits` hold bytes). Stdin over its limit is refused, never cut. A run without a client counts only stderr toward the output limit. When a run ends, its dialogs close and the `exec`, `read_file` and sleeps it waits for stop. A run with a client reads pane text only when `Control.allowReadText` is on too. Trace a run through cancel, the client leaving and the time limit, and check that each frees its slot in `Scripts.commandRunLimit`.
- **State** (`ScriptState`): a JSON object up to 256 KiB, depth 16, 8,192 values. Writes use a revision compare-and-swap under `QLockFile` and `QSaveFile`. Reads refuse symlinks. A `migrate` result is committed only after the replacement loads, and a failed commit keeps the old instance.
- **Contract sync**: `afterglow.d.luau` must match the prelude's helper names, parameters and defaults, `Kinds[]`, and the docs/SCRIPTING.md tables and limits. A command limit also lives in `Settings.cpp`, `CommandSocket.h`, `libs/afterglow-proto/include/AfterglowProto/Run.h` and docs/CONTROL.md. A limit stated in three places (prelude, ScriptHost, docs) must agree.
- **Module-level state** survives a reload only while the source is unchanged. (PlasmaZones algorithms forbid module-level mutable state. The two contracts differ by design.)
- **Licensing**: scripting C++, `afterglow.luau`, `afterglow.d.luau` and example Luau are GPL-3.0-or-later. Package shader packs are LGPL-2.1-or-later (`phosphor-works:shader-reviewer` checks them).

## Known past-bug shapes

- An explicit `metadata.id` clash was resolved in filename order, so a system `z.luau` beat a user `a.luau`. Check that `performScan` keeps directory priority through id resolution.
- A loose script that failed its first load had no file watch, so fixing it never reloaded. Every discovered candidate, failed or superseded, must stay in `watched`.
- `setStateDirectory` was guarded only by a debug assert. A precondition on live state needs a release-build runtime guard.
- An example package sampled the active pane in a timer but wrote to the timer's original `ev.pane`, which `queueResult` keeps. After any wait, timer or result, resolve the target again from the fresh snapshot.
- Documented launch and `exec` options (directions, size, cwd, env) were missing from the prelude and the host. Diff each helper's fields against `Kinds[]`, `d.luau` and the docs table.
- Package shader packs registered under a UUID derived from their id, so `<package>.<pack>` lookups failed until `packagedRef` matching. When a package feature crosses into ShaderLibrary, trace the lookup end to end.
- A docs section landed in the wrong document. `SCRIPTING.md` covers loose scripts and effects. `PACKAGES.md` covers manifests, state, migration and package shaders.

<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# phosphor-works conventions

These rules apply to every phosphor-works repository. Each repository's CLAUDE.md has two parts. The first is the
shared block that `workspace/tools/sync` writes from `workspace/sync/claude-header.md`: the title, where the rules
and tooling come from, and the import of this file. Change it there, never in a repository. The second is the
repository's own, under these sections in this order: `Overview`, `Layout` and `Build and test` (always), then
`Rules`, `Code`, `Skills and agents`, `Other repositories` and `Where things are` (when the repository has some).
A section adds only what this file does not say. When a repository rule and this file disagree, change one of them
so that they agree. `tools/sync --check` reports a block that drifted and a section that is missing, unknown or out
of order.

## The repositories

- Every repository is a sibling checkout under one folder. The `workspace` repository clones them with
  `vcs import --skip-existing --input workspace.repos ..`.
- The `workspace` superbuild builds the libraries and the apps in one tree. Use it to change a library and an app
  together: `cmake --workflow --preset dev` builds everything, and `--preset plasmazones`, `lambent` or `afterglow`
  builds one app against the sibling libraries. Each preset has an `-asan` twin.
- A change that spans repositories is a change set: one branch name in each repository that it touches.
  `workspace/tools/change` makes the branches, opens the pull requests and links them (`start`, `push`), and shows
  the set (`status`). Merge the libraries first. Then move the app's pin to the merged commit: its VERSION, URL,
  FILE and SHA256 together in `cmake/<Project>Dependencies.cmake`, and the same archive in each Nix or packaging
  recipe of the app. `-DCPM_<library>_SOURCE=<dir>` builds an app against a local checkout before the pin moves.
- When the superbuild or the shared tooling finds a problem in one repository, fix it in that repository. Do not add
  a workaround to `workspace`.
- The Claude skills, agents and guard come from the plugins in `workspace/plugins/`. Change them in the `workspace`
  checkout, not in the installed copy under `~/.claude/plugins/`.
- Traps that cost a session are lessons in `workspace/plugins/phosphor-works/lessons/`, not bullets in a CLAUDE.md.
  A prompt hook shows the ones that fit. Record a new one with `phosphor-works:record-lesson`.

## How to work

- Do what was asked, and nothing more. Ask only about real decisions. When the next step is clear, do it.
- Solve the root cause. Do not add workarounds, TODOs or temporary fixes.
- Read a file before you edit it. Put temporary files in the session scratchpad, never in a repository.
- Trust what the user says they did (installed, restarted, tested). Do not question it.
- Never use `sudo`, and never install into the system. To check an install layout, install into a directory under
  `/tmp` (`DESTDIR` or `--prefix`). When a task needs a system package, tell the user which one and why.
- Never touch the user's running desktop or apps: no D-Bus calls to their session, no restarts, no `pkill` or
  `killall`. Test against a nested session with its own bus and display. To stop a process that you started, list
  it with `pgrep -a NAME` and run `kill PID`, never `kill $(pgrep -f ...)`.
- Never commit a secret, a credential or an `.env` file, and never put a token in a command line or a log line.
- The Bash tool runs zsh. Quote a glob that can match nothing (`'*.md'`), and do not start a word with `=`
  (`echo ====` fails).
- Run one build at a time, inside a memory cap:
  `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 <command>`. Without the cap, systemd-oomd can stop
  the user's session. The presets build with 3 jobs.
- A change is finished when it builds with no warnings and its tests pass. A green suite is not proof that a change
  in behavior works: verify it live where the repository's verify skill says so.
- The shared git hooks run clang-format and qmlformat on the staged files and check the commit message.
  `lefthook install` sets them up in a checkout, and `workspace/tools/setup` runs it in every repository.
- `.clang-format`, `.editorconfig`, `CMakePresets.json` and the shared git hooks come from `workspace/tools/sync`
  and `workspace/lefthook/common.yml`. Never change them in a repository: change them in `workspace` and run
  `tools/sync`. Every C++ repository has the presets `dev` (Debug, `build/`), `release`, `relwithdebinfo` and `asan`.
- The C++ CI comes from `workspace/.github/workflows/cpp-ci.yml`. The `ci.yml` of a library, Afterglow or Lambent
  only calls it with what differs (the pin file, the preset, the Nix package check). Change the jobs there, not in a
  repository. A warning fails the build, and the lint checks every tracked C++ and QML file. PlasmaZones still has
  its own `ci.yml`. Every repository uses the shared CI and hooks at one tag of `workspace`, which `tools/sync`
  writes. A change to them reaches the repositories with a new tag and a change set.
- Example programs live in `examples/` at the repository root, never inside a library or app directory. They are
  built only with an option that is off by default (`PHOSPHOR_LIBS_BUILD_EXAMPLES`,
  `PHOSPHOR_SHELL_LIBS_BUILD_EXAMPLES`), so CI and the apps never build them. A test that needs an example builds it
  as its own fixture or reads it as data, so the example cannot fall behind.
- Work on a branch. Never push to `main`. Stage files by name, never with `git add -A` or `git add .`.
- Land work through a pull request, and merge your own pull request when every check passes. A flaky check gets a
  root-cause fix, not a re-run. Leave pull requests that you did not open alone: the user's, other sessions' and
  contributors'.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) in every repository.

- Subject: `<type>(<scope>): <description>`. The scope is optional. Add `!` after the type or scope for a breaking
  change.
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Write the description in the imperative mood, in lowercase, with no full stop at the end.
- In the body, say what changed, why, and how you verified it. Check each claim against the staged diff.
- Merge and revert commits keep the subject that git gives them.

## Writing

Write all text in controlled English, after the principles of
[ASD-STE100, Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf). These rules do not claim full
compliance with the standard's dictionary.

All text means every text in a repository and around it:

- User-facing text: UI strings, setting descriptions, pack and data metadata, `.desktop` files, AppStream metadata,
  package descriptions, CHANGELOG entries and documentation.
- Developer text: READMEs, `docs/`, CLAUDE.md files, code comments and log messages.
- The Claude Code plugins: skills, agents, review notes and lessons.
- Commit messages and pull request descriptions.

Text that is not ours keeps its words: code, commands, paths and identifiers, quotations, and the names and messages
of other projects. A machine check covers user-facing text where a repository has one. Review covers the rest.
Existing text that breaks a rule is corrected when a change edits it. Do not rewrite unrelated text in bulk.

Sentences and procedures:

- Use active voice and present tense where possible.
- Give each term one meaning, and use the same term for the same item.
- Use American spelling.
- Keep a procedural sentence to 20 words or fewer, and a descriptive sentence to 25 words or fewer.
- Give one instruction in each numbered step.
- State the condition before the instruction when the condition affects the action.
- Separate actions from their expected results.
- Use tables for fields, choices, limits and comparisons.
- State limits with units, and say what happens at the limit.
- Keep code, commands, paths, option names and API identifiers exactly as they are.

Punctuation and style:

- Do not join clauses with an em dash or a semicolon. Do not use a spaced hyphen as a dash.
- Do not use a colon for effect ("Label: payload"). Real field labels are correct.
- Do not use rule-of-three lists or "not just X, but Y" for effect.

Technical terms can stay when ordinary words would lose precision (for example Luau, QRhi, Wayland, layer-shell,
shader, pane). Explain a new term at its first use when the reader needs it.

Keep each README to the product's purpose, its main features and links to the documents. Put procedures, API
details, limits and examples in the linked documents. Do not put audit reports, plans or session summaries in a
repository.

## Licenses

- Every file that can hold a comment starts with `SPDX-FileCopyrightText: 2026 Phosphor Works Team` and an
  `SPDX-License-Identifier`. Phosphor Works Team is the only holder of the project's own work. A file ported from
  another project also keeps the upstream holder's line, and a contributor's line stays unless the contributor
  agrees to remove it.
- Apps, their tests and their tools are `GPL-3.0-or-later`. Libraries, including their own tests, are
  `LGPL-2.1-or-later`.
- A format with no comment syntax (JSON) has no header. `REUSE.toml` licenses such files where a repository has one.
- Code that moves from a GPL tree into an LGPL library is a relicense. It needs the agreement of every copyright
  holder. Check it before the move.

## C++ and QML

- C++20, `#pragma once`, `explicit` on single-argument constructors, `override` on virtuals.
- Members are `m_camelCase`. Classes are `PascalCase`, functions `camelCase`.
- `Q_EMIT`, `Q_SIGNALS:` and `Q_SLOTS:`. Emit a signal only when the value changed.
- QObjects are owned by their parent. Otherwise use `std::unique_ptr` or `QPointer`. Never use a manual `delete`.
- `QT_NO_CAST_FROM_ASCII` is on: use `QStringLiteral` for constants and paths, and `QLatin1String` for comparisons
  and JSON keys.
- Format C++ with `clang-format -i` and QML with `qmlformat -i`. Every C++ repository uses the shared
  `.clang-format`. The pre-commit hooks format the staged files.
- QML: Qt Quick 6, typed properties instead of `var`, `required property` for mandatory properties, and bindings
  instead of JavaScript assignments. List every QML file of a module in its `qt_add_qml_module`.

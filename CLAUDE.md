<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

<!-- BEGIN shared: tools/sync writes this block from workspace/sync/claude-header.md. Change it there. -->
# workspace

This file has two parts. The rules that every phosphor-works repository follows come first, from the conventions of
the workspace repository, imported below. The sections after them belong to this repository only: what it is, its
layout, how to build and test it, and its own rules, code, skills and agents, and links to the other repositories.
A section here does not repeat a convention. When a section and the conventions disagree, change one of them so
that they agree.

The Claude Code tooling comes from the plugins that `.claude/settings.json` enables and `workspace/tools/setup`
installs. The `phosphor-works` plugin has the command guard, the shared skills (`phosphor-works:build`, `debug`,
`code-audit`, `record-lesson`, `new-repo`), the shared reviewers, and the lesson index, which adds the lessons that
fit each prompt.

@claude/conventions.md
<!-- END shared -->

## Overview

The dev workspace of the phosphor-works repos: the manifest that clones them side by side, the CMake superbuild
that builds them in one tree, the CI and tooling they share, and the Claude Code plugins every repo uses. It is for
development only. `packaging` owns releases, rebuild watching and CI images, and never builds through this repo.

## Layout

| Path | What |
| --- | --- |
| `workspace.repos` | The vcstool manifest of every repo, cloned as siblings of this one |
| `CMakeLists.txt`, `CMakePresets.json` | The superbuild and its presets: everything (`dev`, `release`, `relwithdebinfo`, `asan`) or one app against the sibling libraries (`plasmazones`, `lambent`, `afterglow`, each with `-asan`) |
| `tools/setup` | Clones the missing repos, registers this checkout as the plugin marketplace, installs the plugins in each repo, sets up the lesson index |
| `tools/snapshot` | The exact commit of every repo, as a vcstool manifest |
| `LICENSES/` | The license texts (REUSE): `GPL-3.0-or-later` for this repo's code, `CC0-1.0` for its configuration, and `LGPL-2.1-or-later`, which `tools/new-repo` copies into a library repository with the other two |
| `tools/new-repo`, `templates/` | A new library repository or program, generated from the templates with every convention, and registered here (`phosphor-works:new-repo`) |
| `tools/change` | Change sets: the branch in each repo, the linked pull requests, the status of the set, the superbuild of the set |
| `tools/sync`, `sync/` | The files every repo holds the same (`.clang-format`, `.editorconfig`, the generated `CMakePresets.json`, the shared block of each CLAUDE.md from `sync/claude-header.md`), the check that each repo's `lefthook.yml` pulls the shared hooks, and the workspace tag (`ref`) that every repo uses the shared CI and hooks at. `tools/sync --check` reports drift, nightly too |
| `lefthook/common.yml` | The shared git hooks: clang-format, qmlformat, the Conventional Commits check |
| `claude/conventions.md` | The rules every repo's CLAUDE.md imports |
| `.claude-plugin/marketplace.json`, `plugins/` | The Claude Code plugins: `phosphor-works` (shared) and one per app |
| `plugins/phosphor-works/lessons/` | The lessons, one file each, that the lesson index searches |
| `.github/workflows/` | `cpp-ci.yml` (the CI every C++ repo calls), `flake-update.yml` (weekly `flake.lock` pull requests in every repo with a flake), `superbuild.yml` (nightly, pull requests that change a build input with the change set of their branch, change sets by hand), `templates.yml` (generates a library repository and an app from `templates/` and checks and builds them, when the templates, the generator or `tools/sync` change) and `plugins.yml` |

## Build and test

### The superbuild

- It points each library's CPM package at the sibling checkout and adds the apps. The first app that asks for a
  library adds it. Five "version overridden" warnings from CPM are expected.
- This file and `CMakeLists.txt` hold only what exists because several repos share one tree (testing at the root,
  one set of install directories).
- Check a change with a build and the tests, not a configure alone: `cmake --workflow --preset dev`. The nightly CI
  builds `relwithdebinfo`, as the apps' own CI does.

### The plugins

Before a pull request that changes the plugins, run `claude plugin validate .` and
`claude plugin validate plugins/<plugin>`, `python3 -I plugins/phosphor-works/hooks/guard/test_guard.py`, and
`sh plugins/phosphor-works/hooks/lessons/lessons.sh check`. The Plugins workflow runs the last two.

## Rules

### The plugins

- Skills and agents are `plugins/<plugin>/skills/<name>/SKILL.md` and `plugins/<plugin>/agents/<name>.md`. The
  front matter `name` is the directory or file name, and users call them `<plugin>:<name>`.
- A shared reviewer holds what applies to the whole stack. What applies to one app's code goes to that app's
  `review-notes/<domain>.md`.
- The guard is `plugins/phosphor-works/hooks/guard/`: a shared core and `repos/<repo>.py` for each repo. It is a
  guardrail, not a security boundary: add rules for the plain commands a session types, never for unusual
  spellings. Add a case to `test_guard.py` with each rule.
- A plugin reads no file outside its own directory: an installed plugin is a copy in a cache.

### Repo settings

Each repo's `.claude/settings.json` enables its plugins from the GitHub marketplace. Commit it in the key order that
`claude plugin install` writes, or every install reorders it. When a repo joins the suite, add it to
`workspace.repos`, give it a `.claude/settings.json` and a CLAUDE.md with the shared block and the standard
sections (`tools/sync` writes the block), and add a `repos/<repo>.py` to the guard if it needs rules of its own.

## Other repositories

- An app joins the superbuild when its repo has a `CMakeLists.txt`. Add its single-app presets when it does.

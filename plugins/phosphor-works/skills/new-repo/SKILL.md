---
name: new-repo
description: "Create a new phosphor-works repository, a library repository or a program, set up with every convention and ready to develop: phosphor-libs pinned, presets, shared CI and git hooks, Claude settings, CLAUDE.md, REUSE licensing and a passing test, registered in the workspace. Use when: new repo, new repository, new library, new app, new program, start a project, scaffold, bootstrap a repo."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Create a repository

`workspace/tools/new-repo` writes the repository from `workspace/templates/` and registers it in the workspace. This
skill runs it and does the steps around it. Run every command from the folder that holds the sibling checkouts.

## 1. Settle the names with the user

Ask only what the request does not say.

| Kind | License | Name | Shape |
| --- | --- | --- | --- |
| `library` | `LGPL-2.1-or-later` | `phosphor-<name>-libs`, and its first library `phosphor-<name>` | Libraries in `libs/`, each with its own `CMakeLists.txt`, `project()`, `include/`, `src/`, `tests/` and find_package config, as in phosphor-libs |
| `app` | `GPL-3.0-or-later` (its `libs/` `LGPL-2.1-or-later`) | The program's name in CamelCase, as Afterglow and Lambent | The application in `<app>/` (`src/`, `qml/`, `tests/`, `data/` with the `.desktop` file and AppStream metadata) and its reusable code in `libs/<app>-core`. Application ID `org.phosphor_works.<Name>` |

The description is one sentence of user-facing text (controlled English, ending with a full stop). It goes into the
README, CLAUDE.md, the `.desktop` file and the AppStream summary.

## 2. Generate

```sh
workspace/tools/new-repo phosphor-<name>-libs --kind library --lib phosphor-<name> --description "<sentence>."
workspace/tools/new-repo <Name> --kind app --description "<sentence>."
```

It pins phosphor-libs at the commit `main` has now (archive and SHA-256) and CPM at that tree's pin, writes the files,
runs `tools/sync` for `.clang-format`, `.editorconfig`, `CMakePresets.json` and `lefthook.yml`, adds the repository to
`workspace.repos`, `sync/repos.json` and the superbuild's lists in `workspace/CMakeLists.txt`, and runs `git init`.

## 3. Build and test it

Inside the memory cap of the conventions:

```sh
cd <repo>
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 cmake --workflow --preset dev
```

This builds phosphor-libs too, so the first build is long. Add `-DCPM_phosphor-libs_SOURCE=$PWD/../phosphor-libs` to
the configure to build a local checkout instead of downloading the pin. The build has no warnings and every test
passes, or the template is wrong: fix it in `workspace/templates/`, not in the new repository alone.

For an app, also validate the data files with `desktop-file-validate` and `appstreamcli validate --no-net`. Then
replace the placeholder content with the real one: the `Categories` of the `.desktop` file and the AppStream
`categories`, and an AppStream description of more than one sentence.

## 4. First commit

```sh
lefthook install
git ls-files -z --others --exclude-standard | git add --pathspec-from-file=- --pathspec-file-nul
git commit -m "feat: create <repo> from the workspace template"
```

## 5. Create the GitHub repository: ask first

Creating a repository publishes it. Ask the user: public or private, and confirm the name and the description. Then:

```sh
gh repo create phosphor-works/<repo> --public --description "<sentence>" --source . --push
```

The first commit goes straight to `main`: there is nothing to open a pull request against yet. Every later change
goes through a pull request.

## 6. Land the workspace change

The registration in `workspace` is a pull request like any other: commit `workspace.repos`, `sync/repos.json` and
`CMakeLists.txt` on a branch, open it, and merge it when every check passes. Then run `workspace/tools/setup`, which
installs the Claude Code plugins and the git hooks in the new checkout.

## What it does not set up

| Missing | When it is needed |
| --- | --- |
| A Nix flake (`flake.nix`, `nix/package.nix`) | Before the first package. Copy phosphor-components' and drop `nix: false` from `ci.yml`. Then add the repository to the matrix of `workspace/.github/workflows/flake-update.yml` |
| Translations | When the first user-facing string ships. Follow phosphor-components' catalog |
| A guard file (`hooks/guard/repos/<repo>.py`) | When the repository has commands of its own that a session must not run |
| Website pages | When the project is announced |

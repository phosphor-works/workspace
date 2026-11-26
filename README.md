<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# workspace

workspace is the development setup for each phosphor-works repository. It has a
[vcstool](https://github.com/dirk-thomas/vcstool) manifest that clones the repositories next to each other. It also
has a CMake superbuild that builds the libraries and apps in one tree. It is for development only. `packaging` builds
the releases, never this repository.

## Set up

Clone this repository and import the other repositories:

```sh
mkdir phosphor-works && cd phosphor-works
git clone git@github.com:phosphor-works/workspace.git
cd workspace
vcs import --skip-existing --input workspace.repos ..
```

Each other repository goes next to `workspace/`. Then run `tools/setup`. It also sets up the Claude Code plugins (see
[Claude Code](#claude-code)). You can run it again safely.

Always give `--skip-existing`. Without it, vcstool switches the checkouts that exist already to `main`, and you are
no longer on your branch. Install vcstool with pip or from the AUR (`python-vcstool`).

To work across all repositories:

```sh
vcs status ..                      # branch and changes in each repo
vcs pull ..                        # fast-forward every repo
tools/snapshot > snap.repos        # the exact commit of every repo
```

`vcs import --input snap.repos <dir>` makes that tree again in another location. `tools/snapshot` replaces
`vcs export --exact`, which stops on a repository with no commits.

## Build

```sh
cmake --workflow --preset dev      # configure, build and test everything into build/
cmake --preset dev                 # or one step at a time
cmake --build --preset dev
ctest --preset dev
```

To build one app alone against the sibling library checkouts, in its own build tree:

```sh
cmake --workflow --preset plasmazones   # build-plasmazones/
cmake --workflow --preset lambent       # build-lambent/
cmake --workflow --preset afterglow     # build-afterglow/
```

Each of these presets has an ASan and UBSan twin: `plasmazones-asan`, `lambent-asan`, `afterglow-asan`.

| Preset | Build |
| --- | --- |
| `dev` | Debug, into `build/` |
| `release` | Release |
| `relwithdebinfo` | Release with debug information |
| `asan` | ASan and UBSan |

Each preset builds the tests. Builds and tests run 3 jobs at a time. To change that, give `-j`. On a 16 GB machine,
run one build at a time, in a memory limit. Then systemd-oomd cannot stop your session together with the build:

```sh
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 cmake --workflow --preset dev
```

To build an app against the library commits that it pins, as its CI and packages do, use the presets of the app in
its own checkout (`cd ../PlasmaZones && cmake --list-presets`).

The superbuild builds each library repository from its sibling checkout, not from the commit that each app pins. The
apps get their libraries through CPM, so the superbuild sets `CPM_<library>_SOURCE` to the sibling. The first app that
asks for a library adds it. CPM prints one "version overridden" warning for each library. This warning is expected.
`branding` stays at the release that each app pins, because the apps need the icon trees of its release archive.

To turn an app off, give `-DWORKSPACE_BUILD_<App>=OFF` (`PlasmaZones`, `Lambent`, `Afterglow`, `Facet`,
`Phosphor`). The superbuild skips an app whose checkout has no `CMakeLists.txt`.

`compile_commands.json` at the root of this repository covers each repository, for clangd and Qt Creator.

A build here uses the current checkout of each repository. The CI of each app builds the commits that the app pins.
If a build here fails and the CI of the app does not, the pin of the app is usually behind the `main` of a library.

## New repositories

```sh
tools/new-repo phosphor-<name>-libs --kind library --lib phosphor-<name> --description "<sentence>."
tools/new-repo <Name> --kind app --description "<sentence>."
```

`tools/new-repo` writes a repository next to this one from `templates/`. The new repository has these items:

- phosphor-libs, pinned at its current `main`
- The shared presets, CI and git hooks
- The Claude Code settings
- A CLAUDE.md that imports the conventions
- REUSE licensing
- A test

A library repository has the shape of phosphor-libs. An app has the shape of Afterglow and Lambent. The tool also
adds the repository to `workspace.repos`, `sync/repos.json` and the superbuild.

The `phosphor-works:new-repo` skill runs the tool and does the other steps: the build, the first commit, the GitHub
repository and the pull request of this repository.

The Templates workflow runs on each change to the templates, the generator or `tools/sync`. It generates one
repository of each kind, checks it as `tools/sync --check` does, and builds and tests it.

## Change sets

A change across repositories is a change set. It has one branch name in each repository that it changes.
`tools/change` makes the branches, opens the pull requests and links them:

```sh
tools/change start feat/new-api phosphor-libs PlasmaZones   # the branch, from origin/main, in each repo
tools/change status                                         # commits, pull request and checks of each repo
tools/change push                                           # push, open the missing pull requests, link them all
tools/change build                                          # the superbuild on the set, in GitHub Actions
```

`status`, `push` and `build` take the name of the set. If you give no name, they use the branch of the current
directory. Each pull request of the set gets a "Change set" section that lists the other pull requests. `push`
updates the section when a repository joins the set. The list is in merge order, libraries first. After a library
merges, move the pin of each app to the merged commit before the app merges.

A pull request on `workspace` runs the superbuild with each repository that has the same branch. Thus a set that
includes `workspace` builds there. `tools/change build` is for a set with no `workspace` branch.

## Shared files and hooks

Each repository holds the same `.clang-format` and `.editorconfig`. Each C++ repository holds the same
`CMakePresets.json`:

| Preset | Build |
| --- | --- |
| `dev` | Debug, `build/` |
| `release` | Release |
| `relwithdebinfo` | Release with debug information |
| `asan` | ASan and UBSan at `-O1` |

Each preset has a build, a test and a workflow preset. The shared files come from `sync/`. `sync/repos.json` tells
which repository gets which file, with the cache variables that a repository adds to its presets. Change the shared
files here, never in a repository:

```sh
tools/sync            # write the shared files into every sibling repo
tools/sync --check    # report what differs (the nightly runs it too)
```

The CLAUDE.md of each repository starts with the same block, from `sync/claude-header.md`. The block gives the title,
the source of the shared rules and tooling, and the import of `claude/conventions.md`. `tools/sync` writes it between
its BEGIN and END markers. The remaining part of the file belongs to the repository, under the standard sections in
their order (`SECTIONS` in `tools/sync`). `--check` reports a section that is missing, unknown or in the wrong
position.

`tools/sync --check` also compares the pins. A repository can pin a library that pins a third repository too. Then
the repository must pin the same commit of that third repository, because the first pin wins in the build, and the
library was tested with its own pin. The check reads the pins of the library at the pinned commit from its sibling
checkout. It reports each difference. Fix a difference with a pin bump in the repository.

It also checks the recipes: the Nix, Arch, RPM, Debian and OBS files of each repository. Each archive that a recipe
names must be one that a pin names, in the repository or in a library that it pins. Each Nix hash must be the SHA-256
of its pin. A recipe that keeps an archive of an old pin then fails the check, not a later Nix build.

The git hooks that all repositories share are in `lefthook/common.yml`. They run clang-format and qmlformat on the
staged files, and the Conventional Commits check. The `lefthook.yml` of each repository pulls them through
`remotes:` and adds only its own commands. `tools/setup` runs `lefthook install` in each repository.

Each repository uses the shared CI (`.github/workflows/cpp-ci.yml`) and the shared hooks at one tag of this
repository. That tag is `ref` in `sync/repos.json`. `tools/sync` writes it into the `ci.yml` and `lefthook.yml` of
each repository. `--check` reports a repository at a different ref. A change to `cpp-ci.yml` or
`lefthook/common.yml` gets to the repositories in five steps:

1. Merge the change here.
2. Push the next tag on `main` (`v2` after `v1`). A tag never moves.
3. Set `ref` to the new tag.
4. Run `tools/sync`.
5. Land the result as one change set (`tools/change`), with the `workspace` change to `ref` in it.

To try a change to `cpp-ci.yml` before it has a tag, point the `ci.yml` of one repository at the `workspace` branch.
Do this on a branch of that repository, and do not merge it.

## Claude Code

This repository is a Claude Code plugin marketplace, `phosphor-works`:

| Plugin | Holds |
| --- | --- |
| `phosphor-works` | The parts that each repository uses: the command guard (`hooks/guard/`), the skills `build`, `debug`, `code-audit` (with its Stop hook) and `record-lesson`, the reviewers for the shared stack (`cpp-qt`, `qml`, `wayland`, `build`, `config`, `shader`, `luau`), and `crash-triage`, `source-scout`, `perf-expert` |
| `plasmazones` | PlasmaZones skills (`build` extras, `verify-live`, `add-setting`, `algorithm-api`, `shader-pack`, `shader-theme`, `review-notes`) and agents (`kwin-compositor-reviewer`, the shader-theme art and critique agents) |
| `afterglow` | Afterglow skills (`build` extras, `verify-live`, `debug` extras, `add-setting`, `script-api`, `shader-pack`, `review-notes`) and agents (`vt`, `platform`, `render`, `window` reviewers) |

A shared reviewer reads the `review-notes/<domain>.md` of the app plugin. That file holds the shapes of past bugs of
the app and the checks for its code in the domain.

Skills and agents have the plugin name: `/plasmazones:build`, `phosphor-works:code-audit`, `afterglow:vt-reviewer`.
`claude/conventions.md` holds the rules that each repository follows. The CLAUDE.md of each repository imports it with
`@../workspace/claude/conventions.md` and adds its own rules.

The `.claude/settings.json` of each repository enables the plugins that it uses, from the GitHub marketplace.
`tools/setup` registers this checkout as the marketplace in its place, so the plugins load from here. An edit applies
at the next session or after `/reload-plugins`, with no push. Change the plugins only here, never in the installed
copy under `~/.claude/plugins/`.

Commit the settings of a repository in the key order that `claude plugin install` writes. If you do not, each install
changes the order. To get that order, run the command one time and commit the result.

### Lessons

A trap that cost a session is a lesson. Each lesson is one Markdown file in `plugins/phosphor-works/lessons/`, and
pull requests review lessons as they review code.

`tools/setup` builds a local SQLite index of the lessons in `~/.local/share/phosphor-works/lessons`, outside git. The
index has sqlite-vec embeddings from a local ONNX model, and FTS5 keywords. A prompt hook adds the few lessons that are
nearest to each prompt for that repository. `phosphor-works:lessons` searches when you ask:

```sh
sh plugins/phosphor-works/hooks/lessons/lessons.sh search "ctest passed but nothing ran" --repo PlasmaZones
```

The index follows the files. The next search or prompt embeds a lesson that you added or changed. No lesson text
leaves the computer. `phosphor-works:record-lesson` tells how to write a lesson.

To check a change, use these commands:

| Check | Command |
| --- | --- |
| The marketplace | `claude plugin validate .` |
| One plugin | `claude plugin validate plugins/<plugin>` |
| The tests of the guard | `python3 -I plugins/phosphor-works/hooks/guard/test_guard.py` |
| The front matter of the lessons | `sh plugins/phosphor-works/hooks/lessons/lessons.sh check` |

## License

The code of this repository is licensed under `GPL-3.0-or-later`. Its configuration is licensed under `CC0-1.0`.
`tools/new-repo` copies `LGPL-2.1-or-later` into a library repository with the other two. The license texts are in
`LICENSES/`.

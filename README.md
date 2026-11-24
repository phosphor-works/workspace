# workspace

Development setup for every phosphor-works repository: a [vcstool](https://github.com/dirk-thomas/vcstool)
manifest that clones them side by side, and a CMake superbuild that builds the libraries and apps in one tree.
It is for development only. Releases are built by `packaging`, never through this repo.

## Set up

```sh
mkdir phosphor-works && cd phosphor-works
git clone git@github.com:phosphor-works/workspace.git
cd workspace
vcs import --skip-existing --input workspace.repos ..
```

Every other repo lands next to `workspace/`. Then run `tools/setup`, which also sets up the Claude Code plugins
(see [Claude Code](#claude-code)). It is safe to run again. Always pass `--skip-existing`: without it, vcstool switches
checkouts that already exist to `main` and takes you off your branch. Install vcstool with pip or from the
AUR (`python-vcstool`).

Across all repos:

```sh
vcs status ..                      # branch and changes in each repo
vcs pull ..                        # fast-forward every repo
tools/snapshot > snap.repos        # the exact commit of every repo
```

`vcs import --input snap.repos <dir>` rebuilds that tree elsewhere. `tools/snapshot` stands in for
`vcs export --exact`, which stops on a repo with no commits yet.

## Build

```sh
cmake --workflow --preset dev      # configure, build and test everything into build/
cmake --preset dev                 # or one step at a time
cmake --build --preset dev
ctest --preset dev
```

One app on its own, against the sibling library checkouts, in its own build tree:

```sh
cmake --workflow --preset plasmazones   # build-plasmazones/
cmake --workflow --preset lambent       # build-lambent/
cmake --workflow --preset afterglow     # build-afterglow/
```

Each of those has an ASan and UBSan twin: `plasmazones-asan`, `lambent-asan`, `afterglow-asan`.

Presets for everything: `dev` (Debug, into `build/`), `release`, `relwithdebinfo`, `asan`. Every preset builds
the tests, and builds and tests run 3 jobs at a time. Pass `-j` to change that. On a 16 GB machine, run one build
at a time, inside a memory cap so systemd-oomd cannot take your session down with it:

```sh
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 cmake --workflow --preset dev
```

To build an app against the library commits it pins instead, as its CI and packages do, use the app's own
presets in its own checkout (`cd ../PlasmaZones && cmake --list-presets`).

The superbuild builds every library repo from its sibling checkout, in place of the commit each app pins. The
apps take their libraries through CPM, so the superbuild sets `CPM_<library>_SOURCE` to the sibling, and the
first app that asks for a library adds it. CPM prints one "version overridden" warning per library, which is
expected. `branding` stays at the release each app pins, since the apps need the icon trees its release
archive holds.

Turn an app off with `-DWORKSPACE_BUILD_<App>=OFF` (`PlasmaZones`, `Lambent`, `Afterglow`, `Facet`,
`Phosphor`). An app whose checkout has no `CMakeLists.txt` yet is skipped.

`compile_commands.json` at this repo's root covers every repo, for clangd and Qt Creator.

A build here uses every repo's current checkout, while each app's own CI builds the commits it pins. A failure
here that an app's CI does not show usually means that app's pin is behind a library's `main`.

## Shared files and hooks

Every repo holds the same `.clang-format` and `.editorconfig`, and every C++ repo the same `CMakePresets.json`:
`dev` (Debug, `build/`), `release`, `relwithdebinfo` and `asan` (ASan and UBSan at `-O1`), each with a build, test and
workflow preset. They come from `sync/`, and `sync/repos.json` says which repo gets which, with the cache variables a
repo adds to its presets. Change them here, never in a repo:

```sh
tools/sync            # write the shared files into every sibling repo
tools/sync --check    # report what differs (the nightly runs it too)
```

The git hooks every repo shares are in `lefthook/common.yml`: clang-format and qmlformat on the staged files, and the
Conventional Commits check. Each repo's `lefthook.yml` pulls them through `remotes:` and adds only its own commands.
`tools/setup` runs `lefthook install` in every repo.

## Claude Code

This repo is a Claude Code plugin marketplace, `phosphor-works`:

| Plugin | Holds |
| --- | --- |
| `phosphor-works` | What every repo uses: the command guard (`hooks/guard/`), the skills `build`, `debug`, `code-audit` (with its Stop hook) and `record-lesson`, the reviewers for the shared stack (`cpp-qt`, `qml`, `wayland`, `build`, `config`, `shader`, `luau`), and `crash-triage`, `source-scout`, `perf-expert` |
| `plasmazones` | PlasmaZones skills (`build` extras, `verify-live`, `add-setting`, `algorithm-api`, `shader-pack`, `shader-theme`, `review-notes`) and agents (`kwin-compositor-reviewer`, the shader-theme art and critique agents) |
| `afterglow` | Afterglow skills (`build` extras, `verify-live`, `debug` extras, `add-setting`, `script-api`, `shader-pack`, `review-notes`) and agents (`vt`, `platform`, `render`, `window` reviewers) |

A shared reviewer reads the app plugin's `review-notes/<domain>.md`, which holds that app's past-bug shapes and
code-specific checks for the domain.

Skills and agents carry the plugin name: `/plasmazones:build`, `phosphor-works:code-audit`,
`afterglow:vt-reviewer`. `claude/conventions.md` holds the rules every repo follows. Each repo's CLAUDE.md imports
it with `@../workspace/claude/conventions.md` and adds its own rules.

Each repo's `.claude/settings.json` enables the plugins it uses, from the GitHub marketplace. `tools/setup` registers
this checkout as the marketplace instead, so the plugins load from here: an edit applies at the next session or
`/reload-plugins`, with no push. Change the plugins only here, never in the installed copy under
`~/.claude/plugins/`. Commit a repo's settings in the key order that `claude plugin install` writes, or every install reorders them: run
it once and commit what it leaves.

### Lessons

Traps that cost a session are lessons: one Markdown file each in `plugins/phosphor-works/lessons/`, reviewed in
pull requests like code. `tools/setup` builds a local SQLite index of them in `~/.local/share/phosphor-works/lessons`
(sqlite-vec embeddings from a local ONNX model, plus FTS5 keywords), outside git. A prompt hook adds the few lessons
closest to each prompt for that repo, and `phosphor-works:lessons` searches on demand:

```sh
sh plugins/phosphor-works/hooks/lessons/lessons.sh search "ctest passed but nothing ran" --repo PlasmaZones
```

The index follows the files: an added or changed lesson is embedded at the next search or prompt. No lesson text
leaves the machine. `phosphor-works:record-lesson` says how to write one.

Check a change with `claude plugin validate .` (the marketplace) or `claude plugin validate plugins/<plugin>`, and
run the guard's tests with `python3 -I plugins/phosphor-works/hooks/guard/test_guard.py` and the lessons' front
matter with `sh plugins/phosphor-works/hooks/lessons/lessons.sh check`.

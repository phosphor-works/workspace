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

Every other repo lands next to `workspace/`. Always pass `--skip-existing`: without it, vcstool switches
checkouts that already exist to `main` and takes you off your branch. Install vcstool with pip or from the
AUR (`python-vcstool`).

Across all repos:

```sh
vcs status ..                      # branch and changes in each repo
vcs pull ..                        # fast-forward every repo
vcs export --exact .. > snap.repos # the exact commit of every repo
```

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

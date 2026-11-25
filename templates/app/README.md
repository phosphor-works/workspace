<!-- SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team -->
<!-- SPDX-License-Identifier: @LICENSE@ -->

# @REPO@

@DESCRIPTION@

## Features

- The first feature of @REPO@, in one sentence.

## Install

Build and install @REPO@ from source:

```sh
cmake --workflow --preset release
cmake --install build-release
```

## Build

```sh
cmake --workflow --preset dev
```

This command configures into `build/`, builds and runs the tests. It needs CMake 3.25, Ninja, Qt 6.10 and the KDE
Extra CMake Modules. The first configure downloads the pinned phosphor-libs.

## Contributing

Read the [phosphor-works conventions](https://github.com/phosphor-works/workspace/blob/main/claude/conventions.md)
before you open a pull request. Use Conventional Commits, and write all text in controlled English (ASD-STE100).

## License

@LICENSE@. The license texts are in `LICENSES/`.

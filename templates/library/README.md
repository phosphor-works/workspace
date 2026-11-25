<!-- SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team -->
<!-- SPDX-License-Identifier: @LICENSE@ -->

# @REPO@

@DESCRIPTION@

## Libraries

| Library | What it does |
| --- | --- |
| [@LIB@](libs/@LIB@/README.md) | The first library of @REPO@, in one sentence. |

## Build

```sh
cmake --workflow --preset dev
```

This command configures into `build/`, builds and runs the tests. It needs CMake 3.25, Ninja, Qt 6.10 and the KDE
Extra CMake Modules. The first configure downloads the pinned phosphor-libs.

## Use from an app

An app adds this repository as a CMake subproject with [CPM](https://github.com/cpm-cmake/CPM.cmake). The app pins
one commit by its archive URL and SHA-256:

```cmake
CPMAddPackage(NAME @REPO@
              URL "https://github.com/phosphor-works/@REPO@/archive/<commit>.tar.gz"
              URL_HASH SHA256=<sha256>)
```

The app's `find_package` and `target_link_libraries` calls then find the targets of this repository. To build the
app against a local checkout, configure the app with `-DCPM_@REPO@_SOURCE=/path/to/@REPO@`.

## Contributing

Read the [phosphor-works conventions](https://github.com/phosphor-works/workspace/blob/main/claude/conventions.md)
before you open a pull request. Use Conventional Commits, and write all text in controlled English (ASD-STE100).

## License

@LICENSE@. The license texts are in `LICENSES/`.

<!-- SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team -->
<!-- SPDX-License-Identifier: @LICENSE@ -->

# @REPO@

@DESCRIPTION@

## Build

```sh
cmake --workflow --preset dev
```

This configures into `build/`, builds and runs the tests. It needs CMake 3.25, Ninja, Qt 6.10 and the KDE Extra CMake
Modules. The first configure downloads the pinned phosphor-libs.

## License

@LICENSE@. The license texts are in `LICENSES/`.

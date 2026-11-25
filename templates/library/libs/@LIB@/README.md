<!-- SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team -->
<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->

# @LIB@

What @LIB@ is for, in one paragraph.

## Responsibility

What @LIB@ owns, and what it leaves to the app or to other libraries.

## Key types

| Type | What it does |
| --- | --- |
| `@LIBTARGET@::version()` | Gives the version of the library. |

## Use

```cmake
find_package(@LIBTARGET@ REQUIRED)
target_link_libraries(myapp PRIVATE @LIBTARGET@::@LIBTARGET@)
```

```cpp
#include <@LIBTARGET@/Version.h>

const QString v = @LIBTARGET@::version();
```

## Dependencies

- Qt 6 Core

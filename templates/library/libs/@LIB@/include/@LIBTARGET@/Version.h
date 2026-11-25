// SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
// SPDX-License-Identifier: LGPL-2.1-or-later

#pragma once

#include "@liblower@_export.h"

#include <QString>

namespace @LIBTARGET @{

    /// The version of the library, as project() in its CMakeLists.txt says.
    @LIBUPPER @_EXPORT QString version();

} // namespace @LIBTARGET@

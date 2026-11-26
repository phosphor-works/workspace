// SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
// SPDX-License-Identifier: LGPL-2.1-or-later

#include <@LIBTARGET@/Version.h>

namespace @LIBTARGET@ {

QString version()
{
    return QStringLiteral(@LIBUPPER@_VERSION_STRING);
}

} // namespace @LIBTARGET@

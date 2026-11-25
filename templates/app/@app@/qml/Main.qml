// SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root

    width: 640
    height: 480
    visible: true
    title: Qt.application.displayName

    Label {
        anchors.centerIn: parent
        text: Qt.application.displayName + " " + Qt.application.version
    }
}

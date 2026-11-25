# SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The @AppName@ application: the window's QML module (@AppNs@, a static
# library that the program and the tests both link), the program, and its
# desktop entry and AppStream metadata. Code that another program could use
# goes to a library in libs/ instead.

qt_add_library(@app@_ui STATIC)
qt_add_qml_module(@app@_ui
    URI @AppNs@
    VERSION 1.0
    QML_FILES
        qml/Main.qml
)
target_link_libraries(@app@_ui PUBLIC Qt6::Quick @AppNs@Core::@AppNs@Core)

qt_add_executable(@app@ src/main.cpp)
target_link_libraries(@app@ PRIVATE Qt6::Gui Qt6::Qml Qt6::Quick @app@_uiplugin @AppNs@Core::@AppNs@Core)
install(TARGETS @app@ RUNTIME DESTINATION ${KDE_INSTALL_BINDIR})

install(FILES data/@APPID@.desktop DESTINATION ${KDE_INSTALL_APPDIR})
install(FILES data/@APPID@.metainfo.xml DESTINATION ${KDE_INSTALL_METAINFODIR})

if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

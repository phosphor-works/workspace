# SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# @LIBTARGET@: the first library of @REPO@. It configures alone from this
# directory too, with its own project().

cmake_minimum_required(VERSION 3.16)

set(@LIBUPPER@_VERSION "0.1.0")

# The Qt floor this library requires and advertises in its Config file: the
# tree's QT_MIN_VERSION in-tree, its own value standalone.
if(DEFINED QT_MIN_VERSION)
    set(@LIBUPPER@_QT_MIN ${QT_MIN_VERSION})
else()
    set(@LIBUPPER@_QT_MIN "6.10.0")
endif()

if(NOT PROJECT_VERSION)
    project(@LIBTARGET@ VERSION ${@LIBUPPER@_VERSION} LANGUAGES CXX)
    set(CMAKE_CXX_STANDARD 20)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

include(GenerateExportHeader)

find_package(Qt6 ${@LIBUPPER@_QT_MIN} REQUIRED COMPONENTS Core)

add_library(@LIBTARGET@ SHARED
    src/Version.cpp
)
add_library(@LIBTARGET@::@LIBTARGET@ ALIAS @LIBTARGET@)

generate_export_header(@LIBTARGET@
    EXPORT_FILE_NAME @liblower@_export.h
    EXPORT_MACRO_NAME @LIBUPPER@_EXPORT
)

if(NOT DEFINED KDE_INSTALL_INCLUDEDIR)
    include(GNUInstallDirs)
    set(KDE_INSTALL_INCLUDEDIR ${CMAKE_INSTALL_INCLUDEDIR})
endif()

target_include_directories(@LIBTARGET@
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
        $<INSTALL_INTERFACE:${KDE_INSTALL_INCLUDEDIR}>
)

target_compile_features(@LIBTARGET@ PUBLIC cxx_std_20)
target_compile_definitions(@LIBTARGET@ PRIVATE @LIBUPPER@_VERSION_STRING="${@LIBUPPER@_VERSION}")

target_link_libraries(@LIBTARGET@
    PUBLIC
        Qt6::Core
)

# Install

if(NOT DEFINED KDE_INSTALL_LIBDIR)
    include(GNUInstallDirs)
    set(KDE_INSTALL_LIBDIR ${CMAKE_INSTALL_LIBDIR})
endif()
if(NOT DEFINED KDE_INSTALL_BINDIR)
    include(GNUInstallDirs)
    set(KDE_INSTALL_BINDIR ${CMAKE_INSTALL_BINDIR})
endif()

set_target_properties(@LIBTARGET@ PROPERTIES
    VERSION ${@LIBUPPER@_VERSION}
    SOVERSION 0
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

install(TARGETS @LIBTARGET@
    EXPORT @LIBTARGET@Targets
    LIBRARY DESTINATION ${KDE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${KDE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${KDE_INSTALL_BINDIR}
)
install(DIRECTORY include/@LIBTARGET@
    DESTINATION ${KDE_INSTALL_INCLUDEDIR}
)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/@liblower@_export.h"
    DESTINATION ${KDE_INSTALL_INCLUDEDIR}/@LIBTARGET@
)
install(EXPORT @LIBTARGET@Targets
    FILE @LIBTARGET@Targets.cmake
    NAMESPACE @LIBTARGET@::
    DESTINATION ${KDE_INSTALL_LIBDIR}/cmake/@LIBTARGET@
)

include(CMakePackageConfigHelpers)
configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/@LIBTARGET@Config.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/@LIBTARGET@Config.cmake"
    INSTALL_DESTINATION ${KDE_INSTALL_LIBDIR}/cmake/@LIBTARGET@
)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/@LIBTARGET@ConfigVersion.cmake"
    VERSION ${@LIBUPPER@_VERSION}
    COMPATIBILITY SameMajorVersion
)
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/@LIBTARGET@Config.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/@LIBTARGET@ConfigVersion.cmake"
    DESTINATION ${KDE_INSTALL_LIBDIR}/cmake/@LIBTARGET@
)

# Tests

if(CMAKE_PROJECT_NAME STREQUAL "@LIBTARGET@" OR BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

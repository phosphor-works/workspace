# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The workspace superbuild: every library repo and every app, from the sibling
# checkouts beside this one, in one build tree. For development only. The
# packaging repo never builds through it.
#
# The apps take each library through CPM, so the superbuild points each CPM
# package at its sibling checkout and adds the apps. The first app that asks
# for a library adds the sibling, and CPM hands every later request for the
# same name the copy already added, so each library is in the tree once. CPM
# prints one "version overridden" warning per library, which is expected.
#
# The superbuild does not add the libraries itself: a library sets up ECM, the
# KDE settings and its compile definitions only as the top-level project, and
# otherwise takes them from the app that adds it.

cmake_minimum_required(VERSION 3.25)

project(PhosphorWorkspace LANGUAGES C CXX)

if(NOT PROJECT_IS_TOP_LEVEL)
    message(FATAL_ERROR "The workspace superbuild is a top-level project only.")
endif()

get_filename_component(WORKSPACE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

# ctest from the build root reaches a test only through a CTestTestfile chain
# that starts here, so testing is enabled at this level, before any app.
option(BUILD_TESTING "Build every repo's test suite" OFF)
if(BUILD_TESTING)
    enable_testing()
endif()

# One CPM download cache for the whole tree (third-party archives, branding).
if(NOT DEFINED CPM_SOURCE_CACHE AND NOT DEFINED ENV{CPM_SOURCE_CACHE})
    set(CPM_SOURCE_CACHE "${CMAKE_CURRENT_SOURCE_DIR}/.cache/cpm" CACHE PATH "CPM download cache")
endif()

# Library repos, built from their sibling checkouts instead of the apps' pins.
# branding stays pinned: the apps take its release archive, which holds the
# generated icon trees the source repo does not.
set(WORKSPACE_LIBRARIES
    phosphor-libs
    phosphor-engine-libs
    phosphor-shell-libs
    phosphor-components
    phosphor-surface-packs)
foreach(lib IN LISTS WORKSPACE_LIBRARIES)
    if(NOT EXISTS "${WORKSPACE_ROOT}/${lib}/CMakeLists.txt")
        message(FATAL_ERROR
            "${WORKSPACE_ROOT}/${lib} is missing. Run: vcs import --skip-existing --input workspace.repos ..")
    endif()
    set(CPM_${lib}_SOURCE "${WORKSPACE_ROOT}/${lib}" CACHE PATH "Sibling checkout of ${lib}" FORCE)
endforeach()

# One set of install directories for every app, defined before any of them.
# Otherwise Afterglow's GNUInstallDirs caches the CMAKE_INSTALL_* names in its
# own scope, and on the next configure ECM in PlasmaZones and Lambent warns that
# KDE_INSTALL_* "got its value from CMAKE_INSTALL_*".
find_package(ECM REQUIRED NO_MODULE)
list(APPEND CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
# ECM picks its KF6 variant and Qt tools by QT_MAJOR_VERSION, which no Qt
# package has set yet. Not find_package(Qt6) here: Qt6 includes GNUInstallDirs,
# the very thing that must come after this.
set(QT_MAJOR_VERSION 6)
include(KDEInstallDirs)

# Afterglow adds phosphor-libs by directory, not through CPM. When an app
# before it already added the tree it reuses that one, so this only matters
# when Afterglow is the only app built.
set(AFTERGLOW_PHOSPHOR_LIBS_DIR "${WORKSPACE_ROOT}/phosphor-libs" CACHE PATH
    "phosphor-libs checkout for Afterglow" FORCE)

# Apps, in this order. PlasmaZones adds phosphor-libs, phosphor-engine-libs and
# phosphor-components, Lambent adds phosphor-shell-libs. An app with no
# CMakeLists.txt yet (an empty repo) is skipped.
set(WORKSPACE_APPS PlasmaZones Lambent Afterglow Facet Phosphor)
set(WORKSPACE_BUILT_APPS "")
foreach(app IN LISTS WORKSPACE_APPS)
    option(WORKSPACE_BUILD_${app} "Build ${app} in the workspace" ON)
    if(WORKSPACE_BUILD_${app} AND EXISTS "${WORKSPACE_ROOT}/${app}/CMakeLists.txt")
        add_subdirectory("${WORKSPACE_ROOT}/${app}" "${app}")
        list(APPEND WORKSPACE_BUILT_APPS ${app})
    endif()
endforeach()

if(NOT WORKSPACE_BUILT_APPS)
    message(FATAL_ERROR "No app to build. Every WORKSPACE_BUILD_<app> is OFF or its checkout is missing.")
endif()
message(STATUS "Workspace apps: ${WORKSPACE_BUILT_APPS}")

# One compile_commands.json at the workspace root, for clangd and Qt Creator
# across every repo.
if(CMAKE_EXPORT_COMPILE_COMMANDS)
    file(CREATE_LINK "${CMAKE_BINARY_DIR}/compile_commands.json"
         "${CMAKE_CURRENT_SOURCE_DIR}/compile_commands.json" SYMBOLIC)
endif()

# SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later

find_package(Qt6 REQUIRED COMPONENTS Test)

# Shared test isolation from phosphor-libs: a private D-Bus session and a
# per-test XDG sandbox.
include(PhosphorTestIsolation)

function(@app@_add_test _name)
    add_executable(${_name} ${ARGN})
    set_target_properties(${_name} PROPERTIES AUTOMOC ON)
    target_link_libraries(${_name} PRIVATE Qt6::Test Qt6::Qml Qt6::Quick @app@_uiplugin)
    add_test(NAME ${_name} COMMAND ${_name})
    phosphor_apply_test_isolation(${_name})
    phosphor_append_test_environment(${_name} "QT_QPA_PLATFORM=offscreen")
endfunction()

@app@_add_test(test_main_window test_main_window.cpp)

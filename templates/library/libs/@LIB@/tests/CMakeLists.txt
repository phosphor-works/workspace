# SPDX-FileCopyrightText: @YEAR@ Phosphor Works Team
# SPDX-License-Identifier: LGPL-2.1-or-later

find_package(Qt6 REQUIRED COMPONENTS Test)

# Shared test isolation from phosphor-libs (a private D-Bus session and a
# per-test XDG sandbox), with stand-ins for a standalone configure of this
# library, where the module is not on the path.
if(PHOSPHOR_LIBS_CMAKE_DIR AND EXISTS "${PHOSPHOR_LIBS_CMAKE_DIR}/PhosphorTestIsolation.cmake")
    include(${PHOSPHOR_LIBS_CMAKE_DIR}/PhosphorTestIsolation.cmake)
else()
    function(phosphor_apply_test_isolation _target)
    endfunction()
    function(phosphor_append_test_environment _test_name)
        set_property(TEST ${_test_name} APPEND PROPERTY ENVIRONMENT ${ARGN})
    endfunction()
endif()

function(@liblower@_add_test _name)
    add_executable(${_name} ${ARGN})
    set_target_properties(${_name} PROPERTIES AUTOMOC ON)
    target_compile_features(${_name} PRIVATE cxx_std_20)
    target_link_libraries(${_name} PRIVATE Qt6::Test Qt6::Core @LIBTARGET@::@LIBTARGET@)
    add_test(NAME ${_name} COMMAND ${_name})
    phosphor_apply_test_isolation(${_name})
    set_tests_properties(${_name} PROPERTIES LABELS "@liblower@")
endfunction()

@liblower@_add_test(test_@libsnake@_version test_version.cpp)

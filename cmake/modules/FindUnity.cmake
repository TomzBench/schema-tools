# FindUnity.cmake
#
# Find or fetch the ThrowTheSwitch Unity test framework.
#
# First attempts find_package in CONFIG mode (for system-installed Unity).
# Falls back to FetchContent from GitHub if not found.
#
# Options:
#   UNITY_VERSION       - Git tag to fetch (default: v2.6.1)
#   UNITY_FIND_REQUIRED - If TRUE, failure is fatal (standard find_package behavior)
#
# Imported targets:
#   unity::framework   - The target to link against

if(TARGET unity::framework)
    return()
endif()

# Try system-installed Unity first (exports unity::framework)
find_package(unity CONFIG QUIET)
if(unity_FOUND)
    set(Unity_FOUND TRUE)
    return()
endif()

# Fall back to FetchContent
include(FetchContent)

if(NOT DEFINED UNITY_VERSION)
    set(UNITY_VERSION "v2.6.1")
endif()

FetchContent_Declare(
    unity
    GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
    GIT_TAG ${UNITY_VERSION}
    GIT_SHALLOW TRUE
)

FetchContent_MakeAvailable(unity)

# Suppress MSVC Spectre mitigation warnings (C5045) on Unity sources
if(MSVC AND TARGET unity)
    target_compile_options(unity PRIVATE /wd5045)
endif()

set(Unity_FOUND TRUE)

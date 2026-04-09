# JsmnZephyrToolsConfig.cmake — Zephyr-aware wrappers around JsmnTools
#
# Provides jsmn_zephyr_templates() and jsmn_zephyr_library_templates()
# with Zephyr defaults (plugin discovery, build_dir env) baked in.
# Does NOT auto-bundle — use find_package(JsmnZephyrApplication) for that.
#
# Cache specs are auto-discovered via file(GLOB) from JSMN_ZEPHYR_CACHE_DIR.
# Callers can pass additional SPECS which accumulate with the glob results.
# If the cache dir doesn't exist yet (no bundle ran), the glob is empty — safe.
#
# Example:
#
#   find_package(JsmnZephyrTools REQUIRED)
#
#   jsmn_zephyr_library_templates(
#       TEMPLATES   ${CMAKE_CURRENT_SOURCE_DIR}/api.h.j2  ${CMAKE_CURRENT_BINARY_DIR}/api.h
#                   ${CMAKE_CURRENT_SOURCE_DIR}/api.c.j2  ${CMAKE_CURRENT_BINARY_DIR}/api.c
#   )

find_package(JsmnTools REQUIRED)

# Top-level build dir so the path is stable across app and library targets.
set(JSMN_ZEPHYR_CACHE_DIR ${CMAKE_BINARY_DIR}/jsmn-cache)

# Render templates for a Zephyr application target.
# Defaults are prepended to ${ARGN}: caller's single-value args (PLUGIN, PREFIX)
# override these, while multi-value args (ENV, SPECS) accumulate.
function(jsmn_zephyr_templates)
    file(GLOB _cache_specs ${JSMN_ZEPHYR_CACHE_DIR}/*.yaml)
    jsmn_render(app
        PLUGIN  ${CMAKE_CURRENT_SOURCE_DIR}
        ENV     build_dir=${CMAKE_CURRENT_BINARY_DIR}
        SPECS   ${_cache_specs}
        ${ARGN}
    )
endfunction()

# Render templates for a Zephyr library target.
# Auto-discovers bundled specs from cache. Creates a codegen target and wires
# it as a dependency of ZEPHYR_CURRENT_LIBRARY so generated files exist before
# the library compiles.
function(jsmn_zephyr_library_templates)
    file(GLOB _cache_specs ${JSMN_ZEPHYR_CACHE_DIR}/*.yaml)
    jsmn_render(${ZEPHYR_CURRENT_LIBRARY}_codegen
        PLUGIN  ${CMAKE_CURRENT_SOURCE_DIR}
        ENV     build_dir=${CMAKE_CURRENT_BINARY_DIR}
        SPECS   ${_cache_specs}
        ${ARGN}
    )
    add_dependencies(${ZEPHYR_CURRENT_LIBRARY} ${ZEPHYR_CURRENT_LIBRARY}_codegen)
endfunction()

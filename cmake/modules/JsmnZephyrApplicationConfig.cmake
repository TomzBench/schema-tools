# JsmnZephyrApplicationConfig.cmake — auto-bundling entry point for Zephyr apps
#
# Bundles specs at configure time (find_package), then exposes the
# JsmnZephyrTools render functions for build-time code generation.
#
# Example:
#
#   find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
#   find_package(JsmnZephyrApplication REQUIRED)  # bundles here
#   find_package(Atx REQUIRED)                    # library renders from cache
#
#   jsmn_zephyr_application_templates(
#       TEMPLATES   ${CMAKE_CURRENT_SOURCE_DIR}/app.h.j2  ${CMAKE_CURRENT_BINARY_DIR}/app.h
#   )

execute_process(
  COMMAND python -m jsmn_tools.cli cmake-dir
  OUTPUT_VARIABLE JSMN_TOOLS_MODULES_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE)
find_package(JsmnZephyrTools REQUIRED HINTS "${JSMN_TOOLS_MODULES_DIR}")

# Auto-bundle runs NOW, at find_package() time. CMAKE_CURRENT_SOURCE_DIR and
# CMAKE_CURRENT_BINARY_DIR resolve to the caller's directories (the
# CMakeLists.txt that called find_package), not this config file's location.
# JSMN_ZEPHYR_CACHE_DIR is set by JsmnZephyrTools using CMAKE_BINARY_DIR,
# so app and library targets agree on the same path.
jsmn_bundle(
    PLUGIN  ${CMAKE_CURRENT_SOURCE_DIR}
    OUTDIR  ${JSMN_ZEPHYR_CACHE_DIR}
    ENV     build_dir=${CMAKE_CURRENT_BINARY_DIR}
)

cmake_minimum_required(VERSION 3.20)
project(shared_runtime C)

execute_process(
    COMMAND jsmn cmake-dir
    OUTPUT_VARIABLE JSMN_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE)
find_package(JsmnTools REQUIRED CONFIG HINTS "${JSMN_CMAKE_DIR}")

# Shared runtime — polymorphic core, no specs needed. JT_HAS_FLOAT is PUBLIC
# so component libraries (and main) inherit it, keeping struct layouts and
# the runtime's float paths in sync.
jsmn_render(runtime_gen TEMPLATES
    runtime.h.jinja ${CMAKE_CURRENT_BINARY_DIR}/runtime.h
    runtime.c.jinja ${CMAKE_CURRENT_BINARY_DIR}/runtime.c)
add_library(runtime ${CMAKE_CURRENT_BINARY_DIR}/runtime.c)
target_include_directories(runtime PUBLIC ${CMAKE_CURRENT_BINARY_DIR})
target_compile_definitions(runtime PUBLIC JT_HAS_FLOAT)

# Component A — descriptor tables and typed shims for sensor_reading only.
# PREFIX namespaces the dispatchers (comp_a_decode, comp_a_encode, ...) so
# they don't collide with component-b's at link time.
jsmn_render(component_a_gen
    PREFIX    comp_a_
    SPECS     ${CMAKE_CURRENT_SOURCE_DIR}/component-a.yaml
    TEMPLATES component-a.h.jinja ${CMAKE_CURRENT_BINARY_DIR}/component-a.h
              component-a.c.jinja ${CMAKE_CURRENT_BINARY_DIR}/component-a.c)
add_library(component-a ${CMAKE_CURRENT_BINARY_DIR}/component-a.c)
target_link_libraries(component-a PUBLIC runtime)

# Component B — descriptor tables and typed shims for device_heartbeat only.
jsmn_render(component_b_gen
    PREFIX    comp_b_
    SPECS     ${CMAKE_CURRENT_SOURCE_DIR}/component-b.yaml
    TEMPLATES component-b.h.jinja ${CMAKE_CURRENT_BINARY_DIR}/component-b.h
              component-b.c.jinja ${CMAKE_CURRENT_BINARY_DIR}/component-b.c)
add_library(component-b ${CMAKE_CURRENT_BINARY_DIR}/component-b.c)
target_link_libraries(component-b PUBLIC runtime)

add_executable(main main.c)
target_link_libraries(main PRIVATE component-a component-b)
target_compile_options(main PRIVATE -Os)

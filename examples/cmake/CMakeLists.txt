cmake_minimum_required(VERSION 3.20)
project(sensor C)

# Ask the jsmn CLI where its CMake modules live, then load JsmnToolsConfig.
execute_process(
    COMMAND jsmn cmake-dir
    OUTPUT_VARIABLE JSMN_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE)
find_package(JsmnTools REQUIRED CONFIG HINTS "${JSMN_CMAKE_DIR}")

# Generate sensor.h / sensor.c / jsmn.h from the spec.
jsmn_generate(sensor_codegen
    SPECS   ${CMAKE_CURRENT_SOURCE_DIR}/sensor.yaml
    NAME    sensor
    OUTDIR  ${CMAKE_CURRENT_BINARY_DIR})

# Link the generated codec directly into the executable. Listing sensor.c as
# a source (which is also an OUTPUT of the jsmn_generate custom command in
# this same directory) is enough for CMake to order codegen before compile —
# no add_dependencies() required.
add_executable(main
    main.c
    ${CMAKE_CURRENT_BINARY_DIR}/sensor.c)
target_include_directories(main PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
target_compile_definitions(main PRIVATE JT_HAS_FLOAT)
target_compile_options(main PRIVATE -Os)

cmake_minimum_required(VERSION 3.14)
project(jsmn-forge-e2e LANGUAGES C)

# Load schema-tools cmake modules
find_program(python3 python REQUIRED)
execute_process(
    COMMAND python -m jsmn_forge.cli --cmake-dir OUTPUT_VARIABLE SCHEMA_TOOLS_CMAKE_MODULES_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
find_package(SchemaTools REQUIRED CONFIG HINTS "${SCHEMA_TOOLS_CMAKE_MODULES_DIR}")
schema_tools_runtime_library(foo OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/jsmn-runtime)

# NOTE we peak into runtime.c files, this is more of a unit test.
cmake_path(SET workspace NORMALIZE "${CMAKE_SOURCE_DIR}/../../../")
cmake_path(SET cmake_modules NORMALIZE "${workspace}/cmake/modules")
cmake_path(SET runtime NORMALIZE "${workspace}/codegen/src/jsmn_forge/lang/jsmn/runtime")

list(APPEND CMAKE_MODULE_PATH "${cmake_modules}")
find_package(Unity REQUIRED)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
enable_testing()

add_executable(test_tok test_tok.c)
target_link_libraries(test_tok PRIVATE unity::framework)
target_include_directories(test_tok PRIVATE "${runtime}")
add_test(NAME test_tok COMMAND test_tok)

add_executable(test_tok_ex test_tok_ex.c)
target_link_libraries(test_tok_ex PRIVATE unity::framework)
target_include_directories(test_tok_ex PRIVATE "${runtime}")
add_test(NAME test_tok_ex COMMAND test_tok_ex)

add_executable(test_descriptor test_descriptor.c)
target_link_libraries(test_descriptor PRIVATE unity::framework)
target_include_directories(test_descriptor PRIVATE "${runtime}")
add_test(NAME test_descriptor COMMAND test_descriptor)

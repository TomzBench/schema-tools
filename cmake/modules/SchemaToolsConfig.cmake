set(SchemaTools_FOUND TRUE)
set(SchemaTools_VERSION "0.1.0")
find_program(SchemaTools_EXECUTABLE jsmn-forge-codegen REQUIRED)

# Generate the runtime ONLY
function(schema_tools_runtime_library target)
    cmake_parse_arguments(PARSE_ARGV 1 ARG "" "OUTPUT" "")
    cmake_path(SET runtime NORMALIZE "${ARG_OUTPUT}/runtime.c")
    cmake_path(SET jsmn NORMALIZE "${ARG_OUTPUT}/jsmn.h")

    # Create command to generate our runtime
    add_custom_command(
        OUTPUT ${runtime} ${jsmn} #
        COMMAND ${SchemaTools_EXECUTABLE} runtime --output ${ARG_OUTPUT} #
        COMMENT "schema-tools: generating runtime" #
    )

    # Add the target library
    add_library(${target} STATIC ${runtime})
    target_include_directories(${target} PUBLIC "${OUTPUT}")

endfunction()

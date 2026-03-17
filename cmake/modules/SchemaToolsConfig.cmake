set(SchemaTools_FOUND TRUE)
set(SchemaTools_VERSION "0.1.0")
find_program(SchemaTools_EXECUTABLE jsmn-forge-codegen REQUIRED)

macro(_append_if cond var)
    if(${cond})
        list(APPEND ${var} ${ARGN})
    endif()
endmacro()

function(schema_tools_generate)
    cmake_parse_arguments(ARG "" "TARGET;PREFIX" "SPECS;TEMPLATES;ENV" ${ARGN})

    # Build --template pairs and collect outputs
    list(LENGTH ARG_TEMPLATES templates_len)
    math(EXPR templates_end "${templates_len} - 1")
    foreach(i RANGE 0 ${templates_end} 2)
        math(EXPR j "${i} + 1")
        list(GET ARG_TEMPLATES ${i} tpl)
        list(GET ARG_TEMPLATES ${j} out)
        list(APPEND _template_args --template "${tpl}" "${out}")
        list(APPEND _depends "${tpl}")
        list(APPEND _outputs "${out}")
    endforeach()

    # Build --env args (user-defined template variables)
    foreach(e IN LISTS ARG_ENV)
        list(APPEND _env_args --env "${e}")
    endforeach()

    # Build command args
    set(_args ${ARG_SPECS} ${_template_args} ${_env_args})
    _append_if(ARG_PREFIX _args --prefix "${ARG_PREFIX}")

    add_custom_command(
        OUTPUT ${_outputs}
        COMMAND ${SchemaTools_EXECUTABLE} generate ${_args}
        DEPENDS ${ARG_SPECS} ${_depends}
        COMMENT "schema-tools: generating outputs"
    )

    if(ARG_TARGET)
        add_custom_target(${ARG_TARGET} DEPENDS ${_outputs})
    endif()
endfunction()

cmake_minimum_required(VERSION 3.14)
project(jsmn-forge-unit-tests LANGUAGES C)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/../../cmake/modules")
find_package(Unity REQUIRED)

enable_testing()

# jsmn — header-only, needs one TU to carry the implementation
add_library(jsmn INTERFACE)
target_include_directories(jsmn INTERFACE "${CMAKE_SOURCE_DIR}/../../include")

# jsmn_forge runtime library
add_library(jsmn_forge STATIC "${CMAKE_SOURCE_DIR}/../../lib/jsmn_forge.c")
target_include_directories(jsmn_forge PUBLIC "${CMAKE_SOURCE_DIR}/../../include")
target_link_libraries(jsmn_forge PUBLIC jsmn)

# unit tests
add_executable(test_jsmn_forge test_jsmn_forge.c)
target_link_libraries(test_jsmn_forge PRIVATE jsmn_forge unity::framework)
add_test(NAME test_jsmn_forge COMMAND test_jsmn_forge)

#  jf_decode
#  ├── jsmn_init                                    [external]
#  ├── jsmn_parse                                   [external]
#  │   ├─→ JF_ERR_PARSE                            (r < 0)
#  │   └─→ JF_ERR_TYPE                             (r < 1)
#  └── jf_decode_object ◄─────────────────────────── [also public, see below]
#      └─→ (propagate)
#
#
#  jf_decode_object                                  [public, recursive via
#  JF_OBJECT]
#  ├─→ JF_ERR_TYPE                                  (not JSMN_OBJECT)
#  ├── memset                                        [libc]
#  ├── tok_eq                                        [leaf: bool]
#  ├── tok_is_null                                   [leaf: bool]
#  │   └─→ JF_ERR_TYPE                              (null on non-optional)
#  ├── decode_array
#  │   ├─→ JF_ERR_TYPE                              (not JSMN_ARRAY)
#  │   ├─→ JF_ERR_OVERFLOW                          (count mismatch)
#  │   ├── elem_size                                 [leaf: uint16_t]
#  │   ├── decode_value
#  │   │   ├── tok_bool                              [leaf]
#  │   │   │   ├─→ JF_ERR_TYPE                      (not primitive / not t/f)
#  │   │   │   └─→ JF_OK
#  │   │   ├── decode_unsigned
#  │   │   │   ├── tok_uint                          [leaf]
#  │   │   │   │   ├─→ JF_ERR_TYPE                  (not primitive / non-digit)
#  │   │   │   │   ├─→ JF_ERR_OVERFLOW              (accumulator overflow)
#  │   │   │   │   └─→ JF_OK
#  │   │   │   ├── check_uint_range                  [leaf]
#  │   │   │   │   ├─→ JF_ERR_OVERFLOW              (value > type max)
#  │   │   │   │   ├─→ JF_ERR_TYPE                  (bad type tag)
#  │   │   │   │   └─→ JF_OK
#  │   │   │   └─→ JF_OK
#  │   │   ├── decode_signed
#  │   │   │   ├── tok_int                           [leaf]
#  │   │   │   │   ├─→ JF_ERR_TYPE                  (not primitive / non-digit)
#  │   │   │   │   ├─→ JF_ERR_OVERFLOW              (accumulator / magnitude)
#  │   │   │   │   └─→ JF_OK
#  │   │   │   ├── check_int_range                   [leaf]
#  │   │   │   │   ├─→ JF_ERR_OVERFLOW              (value outside type range)
#  │   │   │   │   ├─→ JF_ERR_TYPE                  (bad type tag)
#  │   │   │   │   └─→ JF_OK
#  │   │   │   └─→ JF_OK
#  │   │   ├── tok_double                            [leaf]
#  │   │   │   ├─→ JF_ERR_TYPE                      (not primitive / strtod fail)
#  │   │   │   ├─→ JF_ERR_OVERFLOW                  (token too long for buf)
#  │   │   │   └─→ JF_OK
#  │   │   ├── [JF_STRING inline]
#  │   │   │   ├─→ JF_ERR_TYPE                      (not JSMN_STRING)
#  │   │   │   ├─→ JF_ERR_OVERFLOW                  (len >= fd->count)
#  │   │   │   └─→ JF_OK
#  │   │   ├── [JF_OBJECT]
#  │   │   │   ├─→ JF_ERR_TYPE                      (no child)
#  │   │   │   └── jf_decode_object                  [recursive ↑]
#  │   │   └─→ JF_ERR_TYPE                          (default / unknown type)
#  │   └── jf_tok_skip                               [leaf: int]
#  ├── decode_value                                  (same subtree as above)
#  ├── jf_tok_skip                                   [leaf: int]
#  ├─→ JF_ERR_REQUIRED                              (missing required field)
#  └── jf_tok_skip → return value                    (success: token count)
#
#
#  jf_encode                                         [public, recursive via
#  JF_OBJECT]
#  ├─→ JF_ERR_BUFFER                                (dlen exhausted, many sites)
#  ├── emit_key                                      [leaf]
#  │   └─→ JF_ERR_BUFFER
#  ├── encode_array
#  │   ├─→ JF_ERR_BUFFER
#  │   ├── elem_size                                 [leaf: uint16_t]
#  │   └── encode_value
#  │       ├── [JF_BOOL inline]
#  │       │   └─→ JF_ERR_BUFFER
#  │       ├── emit_uint                             [leaf]
#  │       │   └─→ JF_ERR_BUFFER
#  │       ├── emit_int
#  │       │   ├── emit_uint                         [leaf]
#  │       │   │   └─→ JF_ERR_BUFFER
#  │       │   └─→ JF_ERR_BUFFER                    (sign byte)
#  │       ├── [JF_FLOAT/DOUBLE inline — snprintf]
#  │       │   └─→ JF_ERR_BUFFER
#  │       ├── emit_str                              [leaf, bounded by maxlen]
#  │       │   └─→ JF_ERR_BUFFER
#  │       ├── [JF_OBJECT]
#  │       │   ├─→ JF_ERR_TYPE                      (no child)
#  │       │   └── jf_encode                         [recursive ↑]
#  │       └─→ JF_ERR_TYPE                          (default / unknown type)
#  ├── encode_value                                  (same subtree as above)
#  └─→ JF_OK                                        (returns byte count)
#
#
#  jf_len                                            [public, recursive via
#  JF_OBJECT]
#  ├── strlen                                        [libc]
#  ├── len_array
#  │   ├── elem_size                                 [leaf: uint16_t]
#  │   └── len_value
#  │       ├── len_uint                              [leaf: uint32_t]
#  │       ├── len_int
#  │       │   └── len_uint                          [leaf: uint32_t]
#  │       ├── [JF_FLOAT/DOUBLE inline — snprintf]
#  │       ├── len_str                               [leaf, bounded by maxlen]
#  │       ├── [JF_OBJECT]
#  │       │   └── jf_len                            [recursive ↑]
#  │       └── 0                                     (default / unknown type)
#  ├── len_value                                     (same subtree as above)
#  └─→ uint32_t                                     (always succeeds)
#
#
#  jf_tok_skip                                       [public, leaf]
#  └─→ int                                          (always succeeds)
#
#  Summary of all possible error returns by entry point:
#
#  Entry point: jf_decode
#  Possible errors: JF_ERR_PARSE, JF_ERR_TYPE, JF_ERR_REQUIRED, JF_ERR_OVERFLOW
#  ────────────────────────────────────────
#  Entry point: jf_decode_object
#  Possible errors: JF_ERR_TYPE, JF_ERR_REQUIRED, JF_ERR_OVERFLOW
#  ────────────────────────────────────────
#  Entry point: jf_encode
#  Possible errors: JF_ERR_BUFFER, JF_ERR_TYPE
#  ────────────────────────────────────────
#  Entry point: jf_len
#  Possible errors: (none — always returns a count)
#  ────────────────────────────────────────
#  Entry point: jf_tok_skip
#  Possible errors: (none — always returns a count)
#
#✻ Crunched for 45s

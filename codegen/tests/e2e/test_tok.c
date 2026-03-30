#include "gen_test.h"
#include "runtime.c"
#include "unity.h"

void
setUp(void)
{
}

void
tearDown(void)
{
}

// clang-format off
#define ST_UINT_TESTS(X)                                                   \
    X(u8,   uint8_t,   "255",        "256")                                \
    X(u16,  uint16_t,  "65535",      "65536")                              \
    X(u32,  uint32_t,  "4294967295", "4294967296")

#define ST_INT_TESTS(X)                                                    \
    X(i8,   int8_t,    "127",        "-128",        "128",        "-129")  \
    X(i16,  int16_t,   "32767",      "-32768",      "32768",      "-32769") \
    X(i32,  int32_t,   "2147483647", "-2147483648", "2147483648", "-2147483649")
// clang-format on

ST_UINT_TESTS(GEN_UINT_TEST)
ST_INT_TESTS(GEN_INT_TEST)

void
test_tok_skip_primitive(void)
{
    const char json[] = "42";
    jsmntok_t toks[1];
    jsmn_parser p;
    jsmn_init(&p);
    jsmn_parse(&p, json, strlen(json), toks, 1);
    TEST_ASSERT_EQUAL_INT(1, tok_skip(toks, 0));
}

void
test_tok_skip_flat_object(void)
{
    const char json[] = "{\"a\":1,\"b\":2}";
    jsmntok_t toks[8];
    jsmn_parser p;
    jsmn_init(&p);
    jsmn_parse(&p, json, strlen(json), toks, 8);

    /* entire object: { "a" 1 "b" 2 } = 5 tokens */
    TEST_ASSERT_EQUAL_INT(5, tok_skip(toks, 0));
    /* key */
    TEST_ASSERT_EQUAL_INT(1, tok_skip(toks, 1));
    /* primitive value */
    TEST_ASSERT_EQUAL_INT(1, tok_skip(toks, 2));
}

void
test_tok_skip_flat_array(void)
{
    const char json[] = "[1,2,3]";
    jsmntok_t toks[8];
    jsmn_parser p;
    jsmn_init(&p);
    jsmn_parse(&p, json, strlen(json), toks, 8);

    /* array + 3 elements = 4 tokens */
    TEST_ASSERT_EQUAL_INT(4, tok_skip(toks, 0));
    /* single element */
    TEST_ASSERT_EQUAL_INT(1, tok_skip(toks, 1));
}

void
test_tok_skip_nested(void)
{
    const char json[] = "{\"a\":{\"b\":[1,2,3]}}";
    jsmntok_t toks[16];
    jsmn_parser p;
    jsmn_init(&p);
    jsmn_parse(&p, json, strlen(json), toks, 16);

    /* root object: all 8 tokens */
    TEST_ASSERT_EQUAL_INT(8, tok_skip(toks, 0));

    /* inner object {b:[1,2,3]}: obj + "b" + arr + 1 + 2 + 3 = 6 */
    TEST_ASSERT_EQUAL_INT(6, tok_skip(toks, 2));

    /* inner array [1,2,3]: arr + 1 + 2 + 3 = 4 */
    TEST_ASSERT_EQUAL_INT(4, tok_skip(toks, 4));
}

void
test_tok_skip_array_of_objects(void)
{
    const char json[] = "[{\"x\":1},{\"y\":2}]";
    jsmntok_t toks[16];
    jsmn_parser p;
    jsmn_init(&p);
    jsmn_parse(&p, json, strlen(json), toks, 16);

    /* root array: arr + {x:1} + {y:2} = 1 + 3 + 3 = 7 */
    TEST_ASSERT_EQUAL_INT(7, tok_skip(toks, 0));

    /* first object {x:1}: obj + "x" + 1 = 3 */
    TEST_ASSERT_EQUAL_INT(3, tok_skip(toks, 1));

    /* second object {y:2}: obj + "y" + 2 = 3 */
    TEST_ASSERT_EQUAL_INT(3, tok_skip(toks, 4));
}

int
main(void)
{
    UNITY_BEGIN();
    ST_UINT_TESTS(REG_UINT_TEST)
    ST_INT_TESTS(REG_INT_TEST)
    RUN_TEST(test_tok_skip_primitive);
    RUN_TEST(test_tok_skip_flat_object);
    RUN_TEST(test_tok_skip_flat_array);
    RUN_TEST(test_tok_skip_nested);
    RUN_TEST(test_tok_skip_array_of_objects);
    return UNITY_END();
}

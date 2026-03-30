#include "gen_test.h"
#include "unity.h"
#define ST_HAS_INT64
#define ST_HAS_FLOAT
#include "runtime.c"

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
    X(u64,  uint64_t,  "18446744073709551615", "18446744073709551616")

#define ST_INT_TESTS(X)                                                    \
    X(i64,  int64_t,   "9223372036854775807",  "-9223372036854775808",     \
                       "9223372036854775808",  "-9223372036854775809")
// clang-format on

ST_UINT_TESTS(GEN_UINT_TEST)
ST_INT_TESTS(GEN_INT_TEST)

void
test_tok_float_basic(void)
{
    float val;
    jsmntok_t t;

    t = tok_from("3.14");
    TEST_ASSERT_EQUAL_INT(0, tok_float("3.14", &t, &val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.14f, val);

    t = tok_from("-0.5");
    TEST_ASSERT_EQUAL_INT(0, tok_float("-0.5", &t, &val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -0.5f, val);

    t = tok_from("0.0");
    TEST_ASSERT_EQUAL_INT(0, tok_float("0.0", &t, &val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, val);
}

void
test_tok_float_exponent(void)
{
    float val;
    jsmntok_t t;

    t = tok_from("1e3");
    TEST_ASSERT_EQUAL_INT(0, tok_float("1e3", &t, &val));
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 1000.0f, val);

    t = tok_from("2.5e-1");
    TEST_ASSERT_EQUAL_INT(0, tok_float("2.5e-1", &t, &val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.25f, val);
}

void
test_tok_float_reject(void)
{
    float val;
    jsmntok_t t;

    /* reject non-numeric */
    t = tok_from("\"hello\"");
    TEST_ASSERT_EQUAL_INT(-1, tok_float("\"hello\"", &t, &val));
}

void
test_tok_double_basic(void)
{
    double val;
    jsmntok_t t;

    t = tok_from("3.141592653589793");
    TEST_ASSERT_EQUAL_INT(0, tok_double("3.141592653589793", &t, &val));
    TEST_ASSERT_TRUE(val > 3.14159265358979 && val < 3.14159265358980);

    t = tok_from("-1.0e308");
    TEST_ASSERT_EQUAL_INT(0, tok_double("-1.0e308", &t, &val));
    TEST_ASSERT_TRUE(val < 0.0);
}

void
test_tok_double_reject_inf(void)
{
    double val;
    jsmntok_t t;

    /* 1e309 overflows to inf — should reject */
    t = tok_from("1e309");
    TEST_ASSERT_EQUAL_INT(-1, tok_double("1e309", &t, &val));
}

int
main(void)
{
    UNITY_BEGIN();
    ST_UINT_TESTS(REG_UINT_TEST)
    ST_INT_TESTS(REG_INT_TEST)
    RUN_TEST(test_tok_float_basic);
    RUN_TEST(test_tok_float_exponent);
    RUN_TEST(test_tok_float_reject);
    RUN_TEST(test_tok_double_basic);
    RUN_TEST(test_tok_double_reject_inf);
    return UNITY_END();
}

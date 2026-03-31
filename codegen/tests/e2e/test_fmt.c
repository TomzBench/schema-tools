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

static void
assert_fmt_uint(jt_acc_t val, const char *expect)
{
    uint8_t     sz;
    char        buf[20];
    const char *result = fmt_uint(val, &buf, &sz);
    TEST_ASSERT_EQUAL_MEMORY(expect, result, sz);
}

static void
assert_fmt_int(jt_sacc_t val, const char *expect)
{
    uint8_t     sz;
    char        buf[20];
    const char *result = fmt_int(val, &buf, &sz);
    TEST_ASSERT_EQUAL_MEMORY(expect, result, sz);
}

void
test_fmt_uint_zero(void)
{
    assert_fmt_uint(0, "0");
}

void
test_fmt_uint_single_digit(void)
{
    assert_fmt_uint(1, "1");
    assert_fmt_uint(9, "9");
}

void
test_fmt_uint_multi_digit(void)
{
    assert_fmt_uint(10, "10");
    assert_fmt_uint(255, "255");
    assert_fmt_uint(65535, "65535");
}

void
test_fmt_uint_u32_max(void)
{
    assert_fmt_uint((jt_acc_t)UINT32_MAX, "4294967295");
}

void
test_fmt_int_zero(void)
{
    assert_fmt_int(0, "0");
}

void
test_fmt_int_positive(void)
{
    assert_fmt_int(1, "1");
    assert_fmt_int(42, "42");
    assert_fmt_int(INT32_MAX, "2147483647");
}

void
test_fmt_int_negative(void)
{
    assert_fmt_int(-1, "-1");
    assert_fmt_int(-42, "-42");
}

void
test_fmt_int_i32_min(void)
{
    assert_fmt_int((jt_sacc_t)INT32_MIN, "-2147483648");
}

#ifdef JT_HAS_INT64
void
test_fmt_uint_u64_max(void)
{
    assert_fmt_uint(UINT64_MAX, "18446744073709551615");
}

void
test_fmt_int_i64_max(void)
{
    assert_fmt_int(INT64_MAX, "9223372036854775807");
}

void
test_fmt_int_i64_min(void)
{
    assert_fmt_int(INT64_MIN, "-9223372036854775808");
}
#endif

int
main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_fmt_uint_zero);
    RUN_TEST(test_fmt_uint_single_digit);
    RUN_TEST(test_fmt_uint_multi_digit);
    RUN_TEST(test_fmt_uint_u32_max);
    RUN_TEST(test_fmt_int_zero);
    RUN_TEST(test_fmt_int_positive);
    RUN_TEST(test_fmt_int_negative);
    RUN_TEST(test_fmt_int_i32_min);
#ifdef JT_HAS_INT64
    RUN_TEST(test_fmt_uint_u64_max);
    RUN_TEST(test_fmt_int_i64_max);
    RUN_TEST(test_fmt_int_i64_min);
#endif
    return UNITY_END();
}

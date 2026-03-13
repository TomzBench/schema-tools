#ifndef GEN_TEST_H
#define GEN_TEST_H

#include "jsmn.h"
#include "string.h"

static jsmntok_t
tok_from(const char *json)
{
    jsmntok_t t[2];
    jsmn_parser p;
    jsmn_init(&p);
    jsmn_parse(&p, json, strlen(json), t, 2);
    return t[0];
}

#define GEN_UINT_TEST(name, ctype, max_s, over_s)                              \
    void test_tok_##name(void)                                        \
    {                                                                          \
        ctype val;                                                             \
        jsmntok_t t;                                                           \
                                                                               \
        /* zero */                                                             \
        t = tok_from("0");                                                     \
        TEST_ASSERT_EQUAL_INT(0, tok_##name("0", &t, &val));          \
        TEST_ASSERT_EQUAL_UINT(0, val);                                        \
                                                                               \
        /* max */                                                              \
        t = tok_from(max_s);                                                   \
        TEST_ASSERT_EQUAL_INT(0, tok_##name(max_s, &t, &val));        \
        TEST_ASSERT_EQUAL_UINT((ctype) - 1, val);                              \
                                                                               \
        /* overflow */                                                         \
        t = tok_from(over_s);                                                  \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name(over_s, &t, &val));      \
                                                                               \
        /* reject negative */                                                  \
        t = tok_from("-1");                                                    \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name("-1", &t, &val));        \
                                                                               \
        /* reject float */                                                     \
        t = tok_from("1.5");                                                   \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name("1.5", &t, &val));       \
                                                                               \
        /* reject leading zero */                                              \
        t = tok_from("01");                                                    \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name("01", &t, &val));        \
    }

#define GEN_INT_TEST(name, ctype, max_s, min_s, over_s, under_s)               \
    void test_tok_##name(void)                                        \
    {                                                                          \
        ctype val;                                                             \
        jsmntok_t t;                                                           \
                                                                               \
        /* zero */                                                             \
        t = tok_from("0");                                                     \
        TEST_ASSERT_EQUAL_INT(0, tok_##name("0", &t, &val));          \
        TEST_ASSERT_EQUAL_INT(0, val);                                         \
                                                                               \
        /* max */                                                              \
        t = tok_from(max_s);                                                   \
        TEST_ASSERT_EQUAL_INT(0, tok_##name(max_s, &t, &val));        \
                                                                               \
        /* min */                                                              \
        t = tok_from(min_s);                                                   \
        TEST_ASSERT_EQUAL_INT(0, tok_##name(min_s, &t, &val));        \
                                                                               \
        /* overflow */                                                         \
        t = tok_from(over_s);                                                  \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name(over_s, &t, &val));      \
                                                                               \
        /* underflow */                                                        \
        t = tok_from(under_s);                                                 \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name(under_s, &t, &val));     \
                                                                               \
        /* reject float */                                                     \
        t = tok_from("1.5");                                                   \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name("1.5", &t, &val));       \
                                                                               \
        /* reject leading zero */                                              \
        t = tok_from("01");                                                    \
        TEST_ASSERT_EQUAL_INT(-1, tok_##name("01", &t, &val));        \
    }

#define REG_UINT_TEST(name, ctype, max_s, over_s)                              \
    RUN_TEST(test_tok_##name);

#define REG_INT_TEST(name, ctype, max_s, min_s, over_s, under_s)               \
    RUN_TEST(test_tok_##name);

#endif /* GEN_TEST_H */

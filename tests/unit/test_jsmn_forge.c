/*
 * test_jsmn_forge.c — Unit tests for jsmn_forge runtime library
 *
 * Hand-rolled descriptor tables (no codegen dependency).
 * Exercises: scalars, strings, optional fields, nested objects, VLA.
 */

#define JSMN_HEADER
#include "jsmn.h"
/* Provide jsmn implementation in this TU */
#undef JSMN_HEADER
#include "jsmn.h"

#include "jsmn_forge.h"
#include "unity.h"

#include <stddef.h>
#include <string.h>

/* ═══════════════════════════════════════════════════════════════════════
 *  Test structs — hand-rolled, mirrors what codegen would produce
 * ═══════════════════════════════════════════════════════════════════════ */

/* --- optional wrappers --- */

union maybe__bool {
  bool value;
};
struct optional__bool {
  bool present;
  union maybe__bool maybe;
};

union maybe__u32 {
  uint32_t value;
};
struct optional__u32 {
  bool present;
  uint8_t _pad[3];
  union maybe__u32 maybe;
};

/* --- nested object: "point" { int32_t x; int32_t y; } --- */

struct point {
  int32_t x;
  int32_t y;
};

/* --- VLA of uint32_t, capacity 4 --- */

struct vla__u32__n4 {
  uint32_t len;
  uint32_t items[4];
};

/* --- top-level: "widget" --- */

struct widget {
  uint8_t name[32];             /* required string, maxLength 32  */
  int32_t count;                /* required i32                   */
  struct optional__bool active; /* optional bool                  */
  struct optional__u32 score;   /* optional u32                   */
  struct point origin;          /* required nested object         */
  struct vla__u32__n4 tags;     /* required VLA of u32, cap 4     */
};

/* ═══════════════════════════════════════════════════════════════════════
 *  Descriptors
 * ═══════════════════════════════════════════════════════════════════════ */

/* point descriptor */

static const struct jf_field point_fields[] = {
    {.name = "x",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct point, x),
     .present = 0,
     .len_offset = 0,
     .count = 0,
     .type = JF_I32,
     .flags = 0},
    {.name = "y",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct point, y),
     .present = 0,
     .len_offset = 0,
     .count = 0,
     .type = JF_I32,
     .flags = 0},
};

static const struct jf_struct point_desc = {
    .fields = point_fields,
    .size = (uint16_t)sizeof(struct point),
    .ntoks = 5, /* 1 obj + 2 keys + 2 values */
    .nfields = 2,
    .pad = {0},
};

/* widget descriptor */

static const struct jf_field widget_fields[] = {
    /* name: required string */
    {.name = "name",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct widget, name),
     .present = 0,
     .len_offset = 0,
     .count = 32,
     .type = JF_STRING,
     .flags = 0},

    /* count: required i32 */
    {.name = "count",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct widget, count),
     .present = 0,
     .len_offset = 0,
     .count = 0,
     .type = JF_I32,
     .flags = 0},

    /* active: optional bool */
    {.name = "active",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct widget, active.maybe.value),
     .present = (uint16_t)offsetof(struct widget, active.present),
     .len_offset = 0,
     .count = 0,
     .type = JF_BOOL,
     .flags = JF_F_OPTIONAL},

    /* score: optional u32 */
    {.name = "score",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct widget, score.maybe.value),
     .present = (uint16_t)offsetof(struct widget, score.present),
     .len_offset = 0,
     .count = 0,
     .type = JF_U32,
     .flags = JF_F_OPTIONAL},

    /* origin: required nested object */
    {.name = "origin",
     .child = &point_desc,
     .offset = (uint16_t)offsetof(struct widget, origin),
     .present = 0,
     .len_offset = 0,
     .count = 0,
     .type = JF_OBJECT,
     .flags = 0},

    /* tags: required VLA of u32, capacity 4 */
    {.name = "tags",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct widget, tags.items),
     .present = 0,
     .len_offset = (uint16_t)offsetof(struct widget, tags.len),
     .count = 4,
     .type = JF_U32,
     .flags = JF_F_VLA},
};

/* 1 obj + 6 keys + 6 values (origin expands to 5) = 1+6+5+5 = 17 */
#define WIDGET_NTOKS 20

static const struct jf_struct widget_desc = {
    .fields = widget_fields,
    .size = (uint16_t)sizeof(struct widget),
    .ntoks = WIDGET_NTOKS,
    .nfields = 6,
    .pad = {0},
};

/* ═══════════════════════════════════════════════════════════════════════
 *  Unity setup
 * ═══════════════════════════════════════════════════════════════════════ */

void
setUp(void)
{
}
void
tearDown(void)
{
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Decode tests
 * ═══════════════════════════════════════════════════════════════════════ */

void
test_decode_all_fields_present(void)
{
  const char json[] = "{\"name\":\"gizmo\",\"count\":42,\"active\":true,"
                      "\"score\":100,\"origin\":{\"x\":10,\"y\":20},"
                      "\"tags\":[1,2,3]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_OK, rc);
  TEST_ASSERT_EQUAL_STRING("gizmo", (const char *)w.name);
  TEST_ASSERT_EQUAL_INT32(42, w.count);

  TEST_ASSERT_TRUE(w.active.present);
  TEST_ASSERT_TRUE(w.active.maybe.value);

  TEST_ASSERT_TRUE(w.score.present);
  TEST_ASSERT_EQUAL_UINT32(100, w.score.maybe.value);

  TEST_ASSERT_EQUAL_INT32(10, w.origin.x);
  TEST_ASSERT_EQUAL_INT32(20, w.origin.y);

  TEST_ASSERT_EQUAL_UINT32(3, w.tags.len);
  TEST_ASSERT_EQUAL_UINT32(1, w.tags.items[0]);
  TEST_ASSERT_EQUAL_UINT32(2, w.tags.items[1]);
  TEST_ASSERT_EQUAL_UINT32(3, w.tags.items[2]);
}

void
test_decode_optionals_absent(void)
{
  const char json[] = "{\"name\":\"bare\",\"count\":-7,"
                      "\"origin\":{\"x\":0,\"y\":0},\"tags\":[]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_OK, rc);
  TEST_ASSERT_EQUAL_STRING("bare", (const char *)w.name);
  TEST_ASSERT_EQUAL_INT32(-7, w.count);

  TEST_ASSERT_FALSE(w.active.present);
  TEST_ASSERT_FALSE(w.score.present);

  TEST_ASSERT_EQUAL_UINT32(0, w.tags.len);
}

void
test_decode_optional_null(void)
{
  const char json[] = "{\"name\":\"nil\",\"count\":0,\"active\":null,"
                      "\"origin\":{\"x\":1,\"y\":2},\"tags\":[5]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_OK, rc);
  TEST_ASSERT_FALSE(w.active.present);

  TEST_ASSERT_EQUAL_UINT32(1, w.tags.len);
  TEST_ASSERT_EQUAL_UINT32(5, w.tags.items[0]);
}

void
test_decode_unknown_keys_ignored(void)
{
  const char json[] = "{\"name\":\"unk\",\"count\":1,\"extra\":\"ignored\","
                      "\"origin\":{\"x\":0,\"y\":0,\"z\":99},\"tags\":[]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_OK, rc);
  TEST_ASSERT_EQUAL_STRING("unk", (const char *)w.name);
}

void
test_decode_missing_required_field(void)
{
  /* missing "count" */
  const char json[] =
      "{\"name\":\"bad\",\"origin\":{\"x\":0,\"y\":0},\"tags\":[]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_ERR_REQUIRED, rc);
}

void
test_decode_string_overflow(void)
{
  /* name exceeds maxLength 32 */
  const char json[] = "{\"name\":\"abcdefghijklmnopqrstuvwxyz0123456\","
                      "\"count\":0,\"origin\":{\"x\":0,\"y\":0},\"tags\":[]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_ERR_OVERFLOW, rc);
}

void
test_decode_vla_overflow(void)
{
  /* 5 items exceeds capacity 4 */
  const char json[] = "{\"name\":\"big\",\"count\":0,"
                      "\"origin\":{\"x\":0,\"y\":0},\"tags\":[1,2,3,4,5]}";

  struct widget w;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w, &widget_desc, json, (uint32_t)strlen(json), toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_ERR_OVERFLOW, rc);
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Encode tests
 * ═══════════════════════════════════════════════════════════════════════ */

void
test_encode_all_fields(void)
{
  struct widget w;
  memset(&w, 0, sizeof(w));
  memcpy(w.name, "gizmo", 6);
  w.count = 42;
  w.active.present = true;
  w.active.maybe.value = true;
  w.score.present = true;
  w.score.maybe.value = 100;
  w.origin.x = 10;
  w.origin.y = 20;
  w.tags.len = 2;
  w.tags.items[0] = 7;
  w.tags.items[1] = 8;

  uint8_t buf[256];
  int32_t n = jf_encode(buf, sizeof(buf), &w, &widget_desc);

  TEST_ASSERT_GREATER_THAN(0, n);

  /* Verify by decoding back */
  struct widget w2;
  jsmntok_t toks[WIDGET_NTOKS];
  int32_t rc = jf_decode(
      &w2, &widget_desc, (const char *)buf, (uint32_t)n, toks, WIDGET_NTOKS);

  TEST_ASSERT_EQUAL_INT32(JF_OK, rc);
  TEST_ASSERT_EQUAL_STRING("gizmo", (const char *)w2.name);
  TEST_ASSERT_EQUAL_INT32(42, w2.count);
  TEST_ASSERT_TRUE(w2.active.present);
  TEST_ASSERT_TRUE(w2.active.maybe.value);
  TEST_ASSERT_TRUE(w2.score.present);
  TEST_ASSERT_EQUAL_UINT32(100, w2.score.maybe.value);
  TEST_ASSERT_EQUAL_INT32(10, w2.origin.x);
  TEST_ASSERT_EQUAL_INT32(20, w2.origin.y);
  TEST_ASSERT_EQUAL_UINT32(2, w2.tags.len);
  TEST_ASSERT_EQUAL_UINT32(7, w2.tags.items[0]);
  TEST_ASSERT_EQUAL_UINT32(8, w2.tags.items[1]);
}

void
test_encode_optionals_absent(void)
{
  struct widget w;
  memset(&w, 0, sizeof(w));
  memcpy(w.name, "slim", 5);
  w.count = 0;
  w.origin.x = 0;
  w.origin.y = 0;
  w.tags.len = 0;

  uint8_t buf[256];
  int32_t n = jf_encode(buf, sizeof(buf), &w, &widget_desc);
  TEST_ASSERT_GREATER_THAN(0, n);

  /* absent optionals should not appear in output */
  TEST_ASSERT_NULL(strstr((const char *)buf, "active"));
  TEST_ASSERT_NULL(strstr((const char *)buf, "score"));
}

void
test_encode_buffer_too_small(void)
{
  struct widget w;
  memset(&w, 0, sizeof(w));
  memcpy(w.name, "x", 2);
  w.count = 0;
  w.origin.x = 0;
  w.origin.y = 0;
  w.tags.len = 0;

  uint8_t buf[4]; /* way too small */
  int32_t rc = jf_encode(buf, sizeof(buf), &w, &widget_desc);
  TEST_ASSERT_EQUAL_INT32(JF_ERR_BUFFER, rc);
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Length tests
 * ═══════════════════════════════════════════════════════════════════════ */

void
test_len_matches_encode(void)
{
  struct widget w;
  memset(&w, 0, sizeof(w));
  memcpy(w.name, "len", 4);
  w.count = 999;
  w.active.present = true;
  w.active.maybe.value = false;
  w.origin.x = -1;
  w.origin.y = -2;
  w.tags.len = 1;
  w.tags.items[0] = 42;

  uint32_t predicted = jf_len(&w, &widget_desc);

  uint8_t buf[256];
  int32_t actual = jf_encode(buf, sizeof(buf), &w, &widget_desc);
  TEST_ASSERT_GREATER_THAN(0, actual);
  TEST_ASSERT_EQUAL_UINT32(predicted, (uint32_t)actual);
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Utility tests
 * ═══════════════════════════════════════════════════════════════════════ */

void
test_tok_skip_flat(void)
{
  const char json[] = "{\"a\":1,\"b\":2}";
  jsmn_parser p;
  jsmntok_t toks[10];
  jsmn_init(&p);
  jsmn_parse(&p, json, strlen(json), toks, 10);

  /* skip entire object */
  TEST_ASSERT_EQUAL_INT(5, jf_tok_skip(toks, 0));
  /* skip a string key */
  TEST_ASSERT_EQUAL_INT(1, jf_tok_skip(toks, 1));
  /* skip a primitive value */
  TEST_ASSERT_EQUAL_INT(1, jf_tok_skip(toks, 2));
}

void
test_tok_skip_nested(void)
{
  const char json[] = "{\"a\":{\"b\":[1,2,3]}}";
  jsmn_parser p;
  jsmntok_t toks[10];
  jsmn_init(&p);
  jsmn_parse(&p, json, strlen(json), toks, 10);

  /* skip root: obj{1 pair} = 1 + "a" + val = need to count all */
  int total = jf_tok_skip(toks, 0);
  TEST_ASSERT_EQUAL_INT(8, total); /* obj + "a" + obj + "b" + arr + 1 + 2 + 3 */
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Security test struct — small types to exercise range checking
 * ═══════════════════════════════════════════════════════════════════════ */

struct tiny {
    uint8_t u;
    int8_t s;
};

static const struct jf_field tiny_fields[] = {
    {.name = "u",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct tiny, u),
     .present = 0,
     .len_offset = 0,
     .count = 0,
     .type = JF_U8,
     .flags = 0},
    {.name = "s",
     .child = NULL,
     .offset = (uint16_t)offsetof(struct tiny, s),
     .present = 0,
     .len_offset = 0,
     .count = 0,
     .type = JF_I8,
     .flags = 0},
};

static const struct jf_struct tiny_desc = {
    .fields = tiny_fields,
    .size = (uint16_t)sizeof(struct tiny),
    .ntoks = 5,
    .nfields = 2,
    .pad = {0},
};

#define TINY_NTOKS 8

/* ═══════════════════════════════════════════════════════════════════════
 *  Security tests — overflow and range checking
 * ═══════════════════════════════════════════════════════════════════════ */

void
test_decode_uint_overflow(void)
{
    /* 25-digit number exceeds uint64 max */
    const char json[] = "{\"u\":9999999999999999999999999,\"s\":0}";
    struct tiny t;
    jsmntok_t toks[TINY_NTOKS];
    int32_t rc = jf_decode(
        &t, &tiny_desc, json, (uint32_t)strlen(json), toks, TINY_NTOKS);
    TEST_ASSERT_EQUAL_INT32(JF_ERR_OVERFLOW, rc);
}

void
test_decode_int_overflow(void)
{
    /* number exceeding int64 range */
    const char json[] = "{\"u\":0,\"s\":-9999999999999999999999999}";
    struct tiny t;
    jsmntok_t toks[TINY_NTOKS];
    int32_t rc = jf_decode(
        &t, &tiny_desc, json, (uint32_t)strlen(json), toks, TINY_NTOKS);
    TEST_ASSERT_EQUAL_INT32(JF_ERR_OVERFLOW, rc);
}

void
test_decode_uint_range(void)
{
    /* 300 doesn't fit in uint8 */
    const char json[] = "{\"u\":300,\"s\":0}";
    struct tiny t;
    jsmntok_t toks[TINY_NTOKS];
    int32_t rc = jf_decode(
        &t, &tiny_desc, json, (uint32_t)strlen(json), toks, TINY_NTOKS);
    TEST_ASSERT_EQUAL_INT32(JF_ERR_OVERFLOW, rc);
}

void
test_decode_int_range(void)
{
    /* 200 doesn't fit in int8 */
    const char json[] = "{\"u\":0,\"s\":200}";
    struct tiny t;
    jsmntok_t toks[TINY_NTOKS];
    int32_t rc = jf_decode(
        &t, &tiny_desc, json, (uint32_t)strlen(json), toks, TINY_NTOKS);
    TEST_ASSERT_EQUAL_INT32(JF_ERR_OVERFLOW, rc);
}

void
test_decode_negative_for_unsigned(void)
{
    /* negative number in uint field → tok_uint rejects '-' */
    const char json[] = "{\"u\":-1,\"s\":0}";
    struct tiny t;
    jsmntok_t toks[TINY_NTOKS];
    int32_t rc = jf_decode(
        &t, &tiny_desc, json, (uint32_t)strlen(json), toks, TINY_NTOKS);
    TEST_ASSERT_EQUAL_INT32(JF_ERR_TYPE, rc);
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Main
 * ═══════════════════════════════════════════════════════════════════════ */

int
main(void)
{
  UNITY_BEGIN();

  /* Decode */
  RUN_TEST(test_decode_all_fields_present);
  RUN_TEST(test_decode_optionals_absent);
  RUN_TEST(test_decode_optional_null);
  RUN_TEST(test_decode_unknown_keys_ignored);
  RUN_TEST(test_decode_missing_required_field);
  RUN_TEST(test_decode_string_overflow);
  RUN_TEST(test_decode_vla_overflow);

  /* Encode */
  RUN_TEST(test_encode_all_fields);
  RUN_TEST(test_encode_optionals_absent);
  RUN_TEST(test_encode_buffer_too_small);

  /* Length */
  RUN_TEST(test_len_matches_encode);

  /* Security — overflow and range */
  RUN_TEST(test_decode_uint_overflow);
  RUN_TEST(test_decode_int_overflow);
  RUN_TEST(test_decode_uint_range);
  RUN_TEST(test_decode_int_range);
  RUN_TEST(test_decode_negative_for_unsigned);

  /* Utilities */
  RUN_TEST(test_tok_skip_flat);
  RUN_TEST(test_tok_skip_nested);

  return UNITY_END();
}

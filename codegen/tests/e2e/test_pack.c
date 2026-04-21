#include "runtime.h"
#include "jsmn_generated.h"
#include "unity.h"
#include "util.h"

void
setUp(void)
{
}

void
tearDown(void)
{
}

/* ── Helpers ──────────────────────────────────────────────────────── */

static void
assert_tag_eq(const struct tag *a, const struct tag *b)
{
    TEST_ASSERT_EQUAL_STRING(a->label, b->label);
}

static void
assert_item_eq(const struct item *a, const struct item *b)
{
    TEST_ASSERT_EQUAL_UINT32(a->id, b->id);
    TEST_ASSERT_EQUAL_INT16(a->value, b->value);
    for (int i = 0; i < 4; i++) {
        TEST_ASSERT_EQUAL_UINT32(a->scores[i], b->scores[i]);
    }
}

static void
assert_container_eq(const struct container *a, const struct container *b)
{
    TEST_ASSERT_EQUAL_STRING(a->name, b->name);
    assert_item_eq(&a->item, &b->item);
    TEST_ASSERT_EQUAL_UINT32(a->tags.len, b->tags.len);
    for (uint32_t i = 0; i < a->tags.len; i++) {
        assert_tag_eq(&a->tags.items[i], &b->tags.items[i]);
    }
}

/* ── Pack tests ───────────────────────────────────────────────────── */

void
test_pack_two_structs(void)
{
    struct tag  t = {.label = "hello"};
    struct item it = {.id = 42, .value = -7, .scores = {10, 20, 30, 40}};

    struct jt_part parts[] = {
        {.key = "tag", .data = &t, .type = JSMN_TAG_KEY},
        {.key = "item", .data = &it, .type = JSMN_ITEM_KEY},
    };

    // clang-format off
    const char expect[] =
        "{"
            "\"tag\":{\"label\":\"hello\"},"
            "\"item\":{\"id\":42,\"value\":-7,\"scores\":[10,20,30,40]}"
        "}";
    // clang-format on

    uint8_t buf[256];
    int     rc = jsmn_pack(buf, sizeof(buf), parts, 2);
    TEST_ASSERT_GREATER_THAN_INT(0, rc);
    TEST_ASSERT_EQUAL_INT(sizeof(expect) - 1, rc);
    TEST_ASSERT_EQUAL_MEMORY(expect, buf, rc);
}

/* ── Unpack tests ─────────────────────────────────────────────────── */

void
test_unpack_two_structs(void)
{
    // clang-format off
    const char json[] =
        "{"
            "\"tag\":{\"label\":\"world\"},"
            "\"item\":{\"id\":99,\"value\":5,\"scores\":[1,2,3,4]}"
        "}";
    // clang-format on

    struct tag  t = {0};
    struct item it = {0};

    struct jt_part parts[] = {
        {.key = "tag", .data = &t, .type = JSMN_TAG_KEY},
        {.key = "item", .data = &it, .type = JSMN_ITEM_KEY},
    };

    jsmntok_t toks[32];
    int       rc = jsmn_unpack(toks, 32, json, sizeof(json) - 1, parts, 2);
    TEST_ASSERT_GREATER_THAN_INT(0, rc);

    TEST_ASSERT_EQUAL_STRING("world", t.label);
    TEST_ASSERT_EQUAL_UINT32(99, it.id);
    TEST_ASSERT_EQUAL_INT16(5, it.value);
    TEST_ASSERT_EQUAL_UINT32(1, it.scores[0]);
    TEST_ASSERT_EQUAL_UINT32(4, it.scores[3]);
}

/* ── Roundtrip ────────────────────────────────────────────────────── */

void
test_pack_unpack_roundtrip(void)
{
    struct tag  t = {.label = "round"};
    struct item it = {.id = 7, .value = -1, .scores = {5, 6, 7, 8}};

    struct jt_part enc_parts[] = {
        {.key = "t", .data = &t, .type = JSMN_TAG_KEY},
        {.key = "i", .data = &it, .type = JSMN_ITEM_KEY},
    };

    uint8_t j1[256], j2[256];
    int     n1 = jsmn_pack(j1, sizeof(j1), enc_parts, 2);
    TEST_ASSERT_GREATER_THAN_INT(0, n1);

    struct tag  t2 = {0};
    struct item it2 = {0};

    struct jt_part dec_parts[] = {
        {.key = "t", .data = &t2, .type = JSMN_TAG_KEY},
        {.key = "i", .data = &it2, .type = JSMN_ITEM_KEY},
    };

    jsmntok_t toks[32];
    int       nd = jsmn_unpack(toks, 32, (const char *)j1, n1, dec_parts, 2);
    TEST_ASSERT_EQUAL_INT(n1, nd);

    struct jt_part enc2_parts[] = {
        {.key = "t", .data = &t2, .type = JSMN_TAG_KEY},
        {.key = "i", .data = &it2, .type = JSMN_ITEM_KEY},
    };

    int n2 = jsmn_pack(j2, sizeof(j2), enc2_parts, 2);
    TEST_ASSERT_EQUAL_INT(n1, n2);
    TEST_ASSERT_EQUAL_MEMORY(j1, j2, n1);
}

/* ── Nested struct ────────────────────────────────────────────────── */

// clang-format off
#define TAG_INIT(idx, _)  { .label = "t-" #idx }
// clang-format on

void
test_pack_nested(void)
{
    // clang-format off
    struct container c = {
        .name = "box",
        .item = {.id = 1, .value = 2, .scores = {0, 0, 0, 0}},
        .tags = VLA(2, TAG_INIT(0, ), TAG_INIT(1, )),
    };
    // clang-format on

    struct jt_part parts[] = {
        {.key = "c", .data = &c, .type = JSMN_CONTAINER_KEY},
    };

    uint8_t   j1[512];
    int       n1 = jsmn_pack(j1, sizeof(j1), parts, 1);
    TEST_ASSERT_GREATER_THAN_INT(0, n1);

    struct container c2 = {0};
    struct jt_part   dec_parts[] = {
        {.key = "c", .data = &c2, .type = JSMN_CONTAINER_KEY},
    };

    jsmntok_t toks[64];
    int       nd = jsmn_unpack(toks, 64, (const char *)j1, n1, dec_parts, 1);
    TEST_ASSERT_EQUAL_INT(n1, nd);
    assert_container_eq(&c, &c2);
}

/* ── Error cases ──────────────────────────────────────────────────── */

void
test_pack_buffer_too_small(void)
{
    struct tag     t = {.label = "hello"};
    struct jt_part parts[] = {
        {.key = "tag", .data = &t, .type = JSMN_TAG_KEY},
    };

    uint8_t buf[4]; // way too small
    int     rc = jsmn_pack(buf, sizeof(buf), parts, 1);
    TEST_ASSERT_EQUAL_INT(JT_ERR_BUFFER, rc);
}

void
test_unpack_missing_key(void)
{
    const char json[] = "{\"tag\":{\"label\":\"x\"}}";

    struct tag  t = {0};
    struct item it = {0};
    it.id = 999; // sentinel — should not be touched

    struct jt_part parts[] = {
        {.key = "tag", .data = &t, .type = JSMN_TAG_KEY},
        {.key = "item", .data = &it, .type = JSMN_ITEM_KEY},
    };

    jsmntok_t toks[16];
    int       rc = jsmn_unpack(toks, 16, json, sizeof(json) - 1, parts, 2);
    TEST_ASSERT_GREATER_THAN_INT(0, rc);
    TEST_ASSERT_EQUAL_STRING("x", t.label);
    TEST_ASSERT_EQUAL_UINT32(999, it.id); // untouched
}

void
test_unpack_bad_json(void)
{
    const char json[] = "not json";

    struct tag     t = {0};
    struct jt_part parts[] = {
        {.key = "tag", .data = &t, .type = JSMN_TAG_KEY},
    };

    jsmntok_t toks[8];
    int       rc = jsmn_unpack(toks, 8, json, sizeof(json) - 1, parts, 1);
    TEST_ASSERT_LESS_THAN_INT(0, rc);
}

/* ── Main ─────────────────────────────────────────────────────────── */

int
main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_pack_two_structs);
    RUN_TEST(test_unpack_two_structs);
    RUN_TEST(test_pack_unpack_roundtrip);
    RUN_TEST(test_pack_nested);
    RUN_TEST(test_pack_buffer_too_small);
    RUN_TEST(test_unpack_missing_key);
    RUN_TEST(test_unpack_bad_json);
    return UNITY_END();
}

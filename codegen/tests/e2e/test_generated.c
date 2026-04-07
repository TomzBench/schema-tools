#include "jsmn_generated.h"
#include "runtime.h"
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

/* ── Roundtrip helper ──────────────────────────────────────────────── */
/*                                                                       */
/* Encode src -> json1, decode json1 -> dec, encode dec -> json2.        */
/* Asserts: encode > 0, decode returns same byte count, json1 == json2.  */

// clang-format off
#define ROUNDTRIP(type, TYPE, src, dec)                                         \
    uint8_t jt_j1_[JSMN_##TYPE##_LEN];                                       \
    uint8_t jt_j2_[JSMN_##TYPE##_LEN];                                       \
    int32_t jt_n1_ = jsmn_encode_##type(jt_j1_, sizeof(jt_j1_), (src));      \
    TEST_ASSERT_GREATER_THAN_INT(0, jt_n1_);                                   \
    int32_t jt_nd_ = jsmn_decode_##type(                                     \
        (dec), (const char *)jt_j1_, (uint32_t)jt_n1_);                        \
    TEST_ASSERT_EQUAL_INT(jt_n1_, jt_nd_);                                     \
    int32_t jt_n2_ = jsmn_encode_##type(jt_j2_, sizeof(jt_j2_), (dec));      \
    TEST_ASSERT_EQUAL_INT(jt_n1_, jt_n2_);                                     \
    TEST_ASSERT_EQUAL_MEMORY(jt_j1_, jt_j2_, jt_n1_)
// clang-format on

/* ── Primitives ────────────────────────────────────────────────────── */

static void
assert_every_type_eq(const struct every_type *a, const struct every_type *b)
{
    TEST_ASSERT_EQUAL_UINT8(a->p_u8, b->p_u8);
    TEST_ASSERT_EQUAL_INT8(a->p_i8, b->p_i8);
    TEST_ASSERT_EQUAL_UINT16(a->p_u16, b->p_u16);
    TEST_ASSERT_EQUAL_INT16(a->p_i16, b->p_i16);
    TEST_ASSERT_EQUAL_UINT32(a->p_u32, b->p_u32);
    TEST_ASSERT_EQUAL_INT32(a->p_i32, b->p_i32);
    TEST_ASSERT_EQUAL_UINT64(a->p_u64, b->p_u64);
    TEST_ASSERT_EQUAL_INT64(a->p_i64, b->p_i64);
    TEST_ASSERT_EQUAL(a->p_bool, b->p_bool);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, a->p_f32, b->p_f32);
    TEST_ASSERT_TRUE(a->p_f64 == b->p_f64);
    TEST_ASSERT_EQUAL_STRING(a->p_str, b->p_str);
    for (int i = 0; i < 3; i++) {
        TEST_ASSERT_EQUAL_UINT32(a->p_arr[i], b->p_arr[i]);
    }
    TEST_ASSERT_EQUAL_UINT32(a->p_vla.len, b->p_vla.len);
    for (uint32_t i = 0; i < a->p_vla.len; i++) {
        TEST_ASSERT_EQUAL_UINT32(a->p_vla.items[i], b->p_vla.items[i]);
    }
}

void
test_every_type_zero(void)
{
    struct every_type x = {0};
    uint8_t           encoded[JSMN_EVERY_TYPE_LEN];
    // clang-format off
    const char expect[] =
        "{"
            "\"p_u8\":0,"
            "\"p_i8\":0,"
            "\"p_u16\":0,"
            "\"p_i16\":0,"
            "\"p_u32\":0,"
            "\"p_i32\":0,"
            "\"p_u64\":0,"
            "\"p_i64\":0,"
            "\"p_bool\":false,"
            "\"p_f32\":0,"
            "\"p_f64\":0,"
            "\"p_str\":\"\","
            "\"p_arr\":[0,0,0],"
            "\"p_vla\":[]"
        "}";
    // clang-format on
    int ret = jsmn_encode_every_type(encoded, sizeof(encoded), &x);
    TEST_ASSERT_EQUAL_INT(sizeof(expect) - 1, ret);
    TEST_ASSERT_EQUAL_MEMORY(expect, encoded, ret);
}

void
test_every_type_roundtrip(void)
{
    // clang-format off
    struct every_type dec = {0}, x = {
        .p_u8   = 255,
        .p_i8   = -128,
        .p_u16  = 1000,
        .p_i16  = -1000,
        .p_u32  = 100000,
        .p_i32  = -100000,
        .p_u64  = 9999999999ULL,
        .p_i64  = -9999999999LL,
        .p_bool = true,
        .p_f32  = 1.5f,
        .p_f64  = 2.5,
        .p_str  = "hello",
        .p_arr  = {1, 2, 3},
        .p_vla  = VLA(2, 10, 20),
    };
    // clang-format on
    ROUNDTRIP(every_type, EVERY_TYPE, &x, &dec);
    assert_every_type_eq(&x, &dec);
}

/* ── Objects ───────────────────────────────────────────────────────── */

// clang-format off
#define TAG_INIT(idx, _)  { .label = "tag-" #idx }
#define ITEM_INIT         { .id = 42, .value = -7, .scores = {10, 20, 30, 40} }
// clang-format on

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

void
test_tag_roundtrip(void)
{
    struct tag dec = {0}, x = {.label = "hello"};
    ROUNDTRIP(tag, TAG, &x, &dec);
    assert_tag_eq(&x, &dec);
}

void
test_item_roundtrip(void)
{
    struct item dec = {0}, x = ITEM_INIT;
    ROUNDTRIP(item, ITEM, &x, &dec);
    assert_item_eq(&x, &dec);
}

void
test_container_roundtrip(void)
{
    // clang-format off
    struct container dec = {0}, x = {
        .name = "box",
        .item = ITEM_INIT,
        .tags = VLA(3, LISTIFY(3, TAG_INIT, (, ))),
    };
    // clang-format on
    ROUNDTRIP(container, CONTAINER, &x, &dec);
    assert_container_eq(&x, &dec);
}

/* ── Top-level strings ─────────────────────────────────────────────── */

void
test_top_label_roundtrip(void)
{
    top_label dec = {0};
    top_label x = "hello world";
    ROUNDTRIP(top_label, TOP_LABEL, &x, &dec);
    TEST_ASSERT_EQUAL_STRING(x, dec);
}

/* ── Arrays ────────────────────────────────────────────────────────── */

#define POINT_INIT(idx, _) {.x = (idx) + 1, .y = ((idx) + 1) * 10}

/* array_combos layers: inner=3, middle=4, outer=5
 * NOTE: VLA/LISTIFY can't nest (preprocessor blue-paint rule), so these
 * are inlined as object-like macros instead. */
// clang-format off
#define IV_ { .len = 3, .items = {1, 2, 3} }
#define IF_ {1, 2, 3}
#define MVV_ { .len = 4, .items = {IV_, IV_, IV_, IV_} }
#define MVF_ { .len = 4, .items = {IF_, IF_, IF_, IF_} }
#define MFV_ {IV_, IV_, IV_, IV_}
#define MFF_ {IF_, IF_, IF_, IF_}
// clang-format on

static void
assert_point_eq(const struct point *a, const struct point *b)
{
    TEST_ASSERT_EQUAL_INT32(a->x, b->x);
    TEST_ASSERT_EQUAL_INT32(a->y, b->y);
}

void
test_array_of_objects_roundtrip(void)
{
    // clang-format off
    struct array_of_objects dec = {0}, x = {
        .fixed_points = { LISTIFY(4, POINT_INIT, (, )) },
        .vla_points   = VLA(3, LISTIFY(3, POINT_INIT, (, ))),
    };
    // clang-format on
    ROUNDTRIP(array_of_objects, ARRAY_OF_OBJECTS, &x, &dec);
    for (int i = 0; i < 4; i++) {
        assert_point_eq(&x.fixed_points[i], &dec.fixed_points[i]);
    }
    TEST_ASSERT_EQUAL_UINT32(x.vla_points.len, dec.vla_points.len);
    for (uint32_t i = 0; i < x.vla_points.len; i++) {
        assert_point_eq(&x.vla_points.items[i], &dec.vla_points.items[i]);
    }
}

void
test_array_combos_roundtrip(void)
{
    // clang-format off
    struct array_combos dec = {0}, x = {
        .d_vvv = VLA(2, MVV_, MVV_),
        .d_vvf = VLA(2, MVF_, MVF_),
        .d_vfv = VLA(2, MFV_, MFV_),
        .d_vff = VLA(2, MFF_, MFF_),
        .d_fvv = {MVV_, MVV_, MVV_, MVV_, MVV_},
        .d_fvf = {MVF_, MVF_, MVF_, MVF_, MVF_},
        .d_ffv = {MFV_, MFV_, MFV_, MFV_, MFV_},
        .d_fff = {MFF_, MFF_, MFF_, MFF_, MFF_},
    };
    // clang-format on
    ROUNDTRIP(array_combos, ARRAY_COMBOS, &x, &dec);
    // Spot-check VLA lengths
    TEST_ASSERT_EQUAL_UINT32(2, dec.d_vvv.len);
    TEST_ASSERT_EQUAL_UINT32(4, dec.d_vvv.items[0].len);
    TEST_ASSERT_EQUAL_UINT32(3, dec.d_vvv.items[0].items[0].len);
    // Spot-check leaf values
    TEST_ASSERT_EQUAL_UINT32(1, dec.d_vvv.items[0].items[0].items[0]);
    TEST_ASSERT_EQUAL_UINT32(1, dec.d_fff[0][0][0]);
    TEST_ASSERT_EQUAL_UINT32(3, dec.d_fff[0][0][2]);
}

void
test_top_vla_points_roundtrip(void)
{
    struct top_vla_points dec = {0}, x = VLA(3, LISTIFY(3, POINT_INIT, (, )));
    ROUNDTRIP(top_vla_points, TOP_VLA_POINTS, &x, &dec);
    TEST_ASSERT_EQUAL_UINT32(x.len, dec.len);
    for (uint32_t i = 0; i < x.len; i++) {
        assert_point_eq(&x.items[i], &dec.items[i]);
    }
}

/* ── Rename ────────────────────────────────────────────────────────── */

void
test_rename_sample_roundtrip(void)
{
    // clang-format off
    struct rename_sample dec = {0}, x = {
        .field_alpha  = 42,     // rename-all: snake_case
        .beta_override = 99,    // explicit x-jsmn-rename
        .field_gamma  = true,   // rename-all: snake_case
    };
    // clang-format on
    ROUNDTRIP(rename_sample, RENAME_SAMPLE, &x, &dec);
    TEST_ASSERT_EQUAL_UINT32(x.field_alpha, dec.field_alpha);
    TEST_ASSERT_EQUAL_UINT32(x.beta_override, dec.beta_override);
    TEST_ASSERT_EQUAL(x.field_gamma, dec.field_gamma);
}

void
test_rename_verbatim_roundtrip(void)
{
    // clang-format off
    struct rename_verbatim dec = {0}, x = {
        .camelField  = 7,       // no rename — verbatim
        .simpleField = false,   // no rename — verbatim
    };
    // clang-format on
    ROUNDTRIP(rename_verbatim, RENAME_VERBATIM, &x, &dec);
    TEST_ASSERT_EQUAL_UINT32(x.camelField, dec.camelField);
    TEST_ASSERT_EQUAL(x.simpleField, dec.simpleField);
}

/* ── Optionals ─────────────────────────────────────────────────────── */

#define DETAIL_INIT {.code = 404, .message = "not found"}

static void
assert_detail_eq(const struct detail *a, const struct detail *b)
{
    TEST_ASSERT_EQUAL_UINT16(a->code, b->code);
    TEST_ASSERT_EQUAL_STRING(a->message, b->message);
}

static void
assert_record_eq(const struct record *a, const struct record *b)
{
    TEST_ASSERT_EQUAL_UINT32(a->id, b->id);
    TEST_ASSERT_EQUAL(a->count.present, b->count.present);
    if (a->count.present) {
        TEST_ASSERT_EQUAL_UINT32(a->count.maybe.value, b->count.maybe.value);
    }
    TEST_ASSERT_EQUAL(a->label.present, b->label.present);
    if (a->label.present) {
        TEST_ASSERT_EQUAL_STRING(a->label.maybe.value, b->label.maybe.value);
    }
    TEST_ASSERT_EQUAL(a->detail.present, b->detail.present);
    if (a->detail.present) {
        assert_detail_eq(&a->detail.maybe.value, &b->detail.maybe.value);
    }
    TEST_ASSERT_EQUAL(a->values.present, b->values.present);
    if (a->values.present) {
        TEST_ASSERT_EQUAL_UINT32(a->values.maybe.value.len,
                                 b->values.maybe.value.len);
        for (uint32_t i = 0; i < a->values.maybe.value.len; i++) {
            TEST_ASSERT_EQUAL_UINT32(a->values.maybe.value.items[i],
                                     b->values.maybe.value.items[i]);
        }
    }
}

void
test_detail_roundtrip(void)
{
    struct detail dec = {0}, x = DETAIL_INIT;
    ROUNDTRIP(detail, DETAIL, &x, &dec);
    assert_detail_eq(&x, &dec);
}

void
test_record_required_only(void)
{
    struct record dec = {0}, x = {.id = 99};
    ROUNDTRIP(record, RECORD, &x, &dec);
    TEST_ASSERT_EQUAL_UINT32(99, dec.id);
    TEST_ASSERT_FALSE(dec.count.present);
    TEST_ASSERT_FALSE(dec.label.present);
    TEST_ASSERT_FALSE(dec.detail.present);
    TEST_ASSERT_FALSE(dec.values.present);
}

void
test_record_all_present(void)
{
    // clang-format off
    struct record dec = {0}, x = {
        .id     = 1,
        .count  = { .present = true,  .maybe = { .value = 42 } },
        .label  = { .present = true,  .maybe = { .value = "opt-lbl" } },
        .detail = { .present = true,  .maybe = { .value = DETAIL_INIT } },
        .values = { .present = true,
                    .maybe = { .value = VLA(3, 10, 20, 30) } },
    };
    // clang-format on
    ROUNDTRIP(record, RECORD, &x, &dec);
    assert_record_eq(&x, &dec);
}

void
test_record_partial(void)
{
    // clang-format off
    struct record dec = {0}, x = {
        .id     = 5,
        .count  = { .present = true, .maybe = { .value = 10 } },
        .detail = { .present = true,
                    .maybe = { .value = { .code = 200, .message = "ok" } } },
    };
    // clang-format on
    ROUNDTRIP(record, RECORD, &x, &dec);
    assert_record_eq(&x, &dec);
}

/* ── Error edge cases ──────────────────────────────────────────────── */

void
test_err_missing_required(void)
{
    struct point dec = {0};
    const char   json[] = "{\"x\":1}";
    int32_t      ret = jsmn_decode_point(&dec, json, sizeof(json) - 1);
    TEST_ASSERT_EQUAL_INT(JT_ERR_REQUIRED, ret);
}

void
test_err_type_mismatch(void)
{
    struct point dec = {0};
    const char   json[] = "[1,2]";
    int32_t      ret = jsmn_decode_point(&dec, json, sizeof(json) - 1);
    TEST_ASSERT_EQUAL_INT(JT_ERR_TYPE, ret);
}

void
test_err_string_too_long(void)
{
    struct tag dec = {0};
    /* 25 chars, exceeds maxLength 24 */
    const char json[] = "{\"label\":\"abcdefghijklmnopqrstuvwxy\"}";
    int32_t    ret = jsmn_decode_tag(&dec, json, sizeof(json) - 1);
    TEST_ASSERT_EQUAL_INT(JT_ERR_STR_LENGTH, ret);
}

void
test_err_buffer_too_small(void)
{
    struct point x = {.x = 1, .y = 2};
    uint8_t      buf[2];
    int32_t      ret = jsmn_encode_point(buf, sizeof(buf), &x);
    TEST_ASSERT_EQUAL_INT(JT_ERR_BUFFER, ret);
}

/* ── main ──────────────────────────────────────────────────────────── */

int
main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_every_type_zero);
    RUN_TEST(test_every_type_roundtrip);
    RUN_TEST(test_tag_roundtrip);
    RUN_TEST(test_item_roundtrip);
    RUN_TEST(test_container_roundtrip);
    RUN_TEST(test_top_label_roundtrip);
    RUN_TEST(test_array_of_objects_roundtrip);
    RUN_TEST(test_array_combos_roundtrip);
    RUN_TEST(test_top_vla_points_roundtrip);
    RUN_TEST(test_rename_sample_roundtrip);
    RUN_TEST(test_rename_verbatim_roundtrip);
    RUN_TEST(test_detail_roundtrip);
    RUN_TEST(test_record_required_only);
    RUN_TEST(test_record_all_present);
    RUN_TEST(test_record_partial);
    RUN_TEST(test_err_missing_required);
    RUN_TEST(test_err_type_mismatch);
    RUN_TEST(test_err_string_too_long);
    RUN_TEST(test_err_buffer_too_small);
    return UNITY_END();
}

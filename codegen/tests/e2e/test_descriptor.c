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

/* ── Flat descriptor tables (mirrors codegen output) ──────────────── */

static const struct st_array st_arrays[] = {
    /* [0] fixed array of u32, max=10 */
    {ST_KIND_FIXED, 0, 10, sizeof(uint32_t), ST_PRIM(ST_KIND_U32)},
    /* [1] fixed array of struct[0], max=5 */
    {ST_KIND_FIXED, 0, 5, 8, ST_STRUCT(0)},
};

static const struct st_field st_fields[] = {
    /* [0] u8 field at offset 4, required */
    {0, 4, 0xFFFF, ST_PRIM(ST_KIND_U8)},
};

static const struct st_struct st_structs[] = {
    /* [0] 1 field, size=8, ntoks=3, field0=0 */
    {1, 0, 8, 3, 0},
};

void
test_type_prim(void)
{
    for (uint8_t k = ST_KIND_BOOL; k <= ST_KIND_DOUBLE; k++) {
        st_type_t t = ST_PRIM(k);
        TEST_ASSERT_TRUE(ST_IS_PRIM(t));
        TEST_ASSERT_FALSE(ST_IS_STRUCT(t));
        TEST_ASSERT_FALSE(ST_IS_ARRAY(t));
        TEST_ASSERT_EQUAL_UINT8(k, ST_PRIM_ID(t));
    }
}

void
test_type_array(void)
{
    st_type_t ref = ST_ARRAY(0);
    TEST_ASSERT_TRUE(ST_IS_ARRAY(ref));
    TEST_ASSERT_FALSE(ST_IS_PRIM(ref));
    TEST_ASSERT_FALSE(ST_IS_STRUCT(ref));
    TEST_ASSERT_EQUAL_UINT16(0, ST_IDX(ref));

    const struct st_array *a = &st_arrays[ST_IDX(ref)];
    TEST_ASSERT_EQUAL_UINT8(ST_KIND_FIXED, a->kind);
    TEST_ASSERT_EQUAL_UINT16(10, a->max);
    TEST_ASSERT_EQUAL_UINT16(sizeof(uint32_t), a->elem_size);
    TEST_ASSERT_TRUE(ST_IS_PRIM(a->elem));
    TEST_ASSERT_EQUAL_UINT8(ST_KIND_U32, ST_PRIM_ID(a->elem));
}

void
test_type_struct(void)
{
    st_type_t ref = ST_STRUCT(0);
    TEST_ASSERT_TRUE(ST_IS_STRUCT(ref));
    TEST_ASSERT_FALSE(ST_IS_PRIM(ref));
    TEST_ASSERT_FALSE(ST_IS_ARRAY(ref));
    TEST_ASSERT_EQUAL_UINT16(0, ST_IDX(ref));

    const struct st_struct *s = &st_structs[ST_IDX(ref)];
    TEST_ASSERT_EQUAL_UINT8(1, s->nfields);
    TEST_ASSERT_EQUAL_UINT16(8, s->size);
    TEST_ASSERT_EQUAL_UINT16(3, s->ntoks);

    const struct st_field *f = &st_fields[s->field0];
    TEST_ASSERT_TRUE(ST_IS_PRIM(f->type));
    TEST_ASSERT_EQUAL_UINT8(ST_KIND_U8, ST_PRIM_ID(f->type));
}

void
test_type_array_of_objects(void)
{
    st_type_t ref = ST_ARRAY(1);
    TEST_ASSERT_TRUE(ST_IS_ARRAY(ref));
    TEST_ASSERT_EQUAL_UINT16(1, ST_IDX(ref));

    const struct st_array *a = &st_arrays[ST_IDX(ref)];
    TEST_ASSERT_EQUAL_UINT8(ST_KIND_FIXED, a->kind);
    TEST_ASSERT_EQUAL_UINT16(5, a->max);
    TEST_ASSERT_EQUAL_UINT16(8, a->elem_size);

    /* element type is a struct */
    TEST_ASSERT_TRUE(ST_IS_STRUCT(a->elem));
    TEST_ASSERT_EQUAL_UINT16(0, ST_IDX(a->elem));

    const struct st_struct *inner = &st_structs[ST_IDX(a->elem)];
    TEST_ASSERT_EQUAL_UINT8(1, inner->nfields);
}

int
main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_type_prim);
    RUN_TEST(test_type_array);
    RUN_TEST(test_type_struct);
    RUN_TEST(test_type_array_of_objects);
    return UNITY_END();
}

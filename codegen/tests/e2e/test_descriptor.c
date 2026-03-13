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

static const struct rt_array rt_arrays[] = {
    /* [0] fixed array of u32, max=10 */
    {RT_KIND_FIXED, 0, 10, sizeof(uint32_t), RT_PRIM(RT_KIND_U32)},
    /* [1] fixed array of struct[0], max=5 */
    {RT_KIND_FIXED, 0, 5, 8, RT_STRUCT(0)},
};

static const struct rt_field rt_fields[] = {
    /* [0] u8 field at offset 4, required */
    {0, 4, 0xFFFF, RT_PRIM(RT_KIND_U8)},
};

static const struct rt_struct rt_structs[] = {
    /* [0] 1 field, size=8, ntoks=3, field0=0 */
    {1, 0, 8, 3, 0},
};

void
test_type_prim(void)
{
    for (uint8_t k = RT_KIND_BOOL; k <= RT_KIND_DOUBLE; k++) {
        rt_type_t t = RT_PRIM(k);
        TEST_ASSERT_TRUE(RT_IS_PRIM(t));
        TEST_ASSERT_FALSE(RT_IS_STRUCT(t));
        TEST_ASSERT_FALSE(RT_IS_ARRAY(t));
        TEST_ASSERT_EQUAL_UINT8(k, RT_PRIM_ID(t));
    }
}

void
test_type_array(void)
{
    rt_type_t ref = RT_ARRAY(0);
    TEST_ASSERT_TRUE(RT_IS_ARRAY(ref));
    TEST_ASSERT_FALSE(RT_IS_PRIM(ref));
    TEST_ASSERT_FALSE(RT_IS_STRUCT(ref));
    TEST_ASSERT_EQUAL_UINT16(0, RT_IDX(ref));

    const struct rt_array *a = &rt_arrays[RT_IDX(ref)];
    TEST_ASSERT_EQUAL_UINT8(RT_KIND_FIXED, a->kind);
    TEST_ASSERT_EQUAL_UINT16(10, a->max);
    TEST_ASSERT_EQUAL_UINT16(sizeof(uint32_t), a->elem_size);
    TEST_ASSERT_TRUE(RT_IS_PRIM(a->elem));
    TEST_ASSERT_EQUAL_UINT8(RT_KIND_U32, RT_PRIM_ID(a->elem));
}

void
test_type_struct(void)
{
    rt_type_t ref = RT_STRUCT(0);
    TEST_ASSERT_TRUE(RT_IS_STRUCT(ref));
    TEST_ASSERT_FALSE(RT_IS_PRIM(ref));
    TEST_ASSERT_FALSE(RT_IS_ARRAY(ref));
    TEST_ASSERT_EQUAL_UINT16(0, RT_IDX(ref));

    const struct rt_struct *s = &rt_structs[RT_IDX(ref)];
    TEST_ASSERT_EQUAL_UINT8(1, s->nfields);
    TEST_ASSERT_EQUAL_UINT16(8, s->size);
    TEST_ASSERT_EQUAL_UINT16(3, s->ntoks);

    const struct rt_field *f = &rt_fields[s->field0];
    TEST_ASSERT_TRUE(RT_IS_PRIM(f->type));
    TEST_ASSERT_EQUAL_UINT8(RT_KIND_U8, RT_PRIM_ID(f->type));
}

void
test_type_array_of_objects(void)
{
    rt_type_t ref = RT_ARRAY(1);
    TEST_ASSERT_TRUE(RT_IS_ARRAY(ref));
    TEST_ASSERT_EQUAL_UINT16(1, RT_IDX(ref));

    const struct rt_array *a = &rt_arrays[RT_IDX(ref)];
    TEST_ASSERT_EQUAL_UINT8(RT_KIND_FIXED, a->kind);
    TEST_ASSERT_EQUAL_UINT16(5, a->max);
    TEST_ASSERT_EQUAL_UINT16(8, a->elem_size);

    /* element type is a struct */
    TEST_ASSERT_TRUE(RT_IS_STRUCT(a->elem));
    TEST_ASSERT_EQUAL_UINT16(0, RT_IDX(a->elem));

    const struct rt_struct *inner = &rt_structs[RT_IDX(a->elem)];
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

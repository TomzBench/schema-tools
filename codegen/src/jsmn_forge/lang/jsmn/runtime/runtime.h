#ifndef RUNTIME_H
#define RUNTIME_H

#include "jsmn.h"
#include <stdbool.h>
#include <stdint.h>

/* ── Tagged type handle ─────────────────────────────────────────────── */
/*                                                                       */
/* uint16_t, 2-bit tag in low bits:                                      */
/*   xxxxxxxxxxxxxxx1  →  primitive     (bits[15:1] = scalar ID)         */
/*   xxxxxxxxxxxxx00   →  struct index  (bits[15:2] into rt_structs[])   */
/*   xxxxxxxxxxxxx10   →  array index   (bits[15:2] into rt_arrays[])    */

typedef uint16_t rt_type_t;

#define RT_PRIM(id)     ((rt_type_t)(((id) << 1) | 1u))
#define RT_STRUCT(i)    ((rt_type_t)((i) << 2))
#define RT_ARRAY(i)     ((rt_type_t)(((i) << 2) | 2u))

#define RT_IS_PRIM(t)   ((t) & 1u)
#define RT_IS_STRUCT(t)  (((t) & 3u) == 0)
#define RT_IS_ARRAY(t)   (((t) & 3u) == 2)
#define RT_PRIM_ID(t)    ((t) >> 1)
#define RT_IDX(t)        ((t) >> 2)

/* ── Scalar type IDs (fit in 7 bits) ───────────────────────────────── */

// clang-format off
#define RT_KIND_BOOL   0
#define RT_KIND_CHAR   1
#define RT_KIND_U8     2
#define RT_KIND_I8     3
#define RT_KIND_U16    4
#define RT_KIND_I16    5
#define RT_KIND_U32    6
#define RT_KIND_I32    7
#define RT_KIND_U64    8
#define RT_KIND_I64    9
#define RT_KIND_FLOAT  10
#define RT_KIND_DOUBLE 11

/* Array kind IDs (only appear in rt_array.kind) */
#define RT_KIND_STRING 12
#define RT_KIND_FIXED  13
#define RT_KIND_VLA    14
// clang-format on

/* ── Table entry types (8 bytes each, zero pointers) ───────────────── */

struct rt_field {
    uint16_t  off_name;        // byte offset into rt_names[]
    uint16_t  off_value;       // offsetof to value
    uint16_t  off_present;     // offsetof to bool present, 0xFFFF = required
    rt_type_t type;            // prim / struct idx / array idx
};

struct rt_array {
    uint8_t   kind;            // RT_KIND_STRING / RT_KIND_FIXED / RT_KIND_VLA
    uint8_t   pad;
    uint16_t  max;             // capacity
    uint16_t  elem_size;       // stride in bytes
    rt_type_t elem;            // element type (recursive)
};

struct rt_struct {
    uint8_t   nfields;
    uint8_t   pad;
    uint16_t  size;            // sizeof(struct T)
    uint16_t  ntoks;           // max jsmn tokens needed
    uint16_t  field0;          // start index into rt_fields[]
};

#ifdef __cplusplus
extern "C" {
#endif

int
rt_decode(void *dst,
          const struct rt_struct *desc,
          const char *src,
          uint32_t slen,
          jsmntok_t *toks,
          uint32_t ntoks);

#ifdef __cplusplus
}
#endif

#endif

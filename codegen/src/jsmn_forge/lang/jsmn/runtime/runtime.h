#ifndef RUNTIME_H
#define RUNTIME_H

#include "jsmn.h"
#include <stdbool.h>
#include <stdint.h>

/* ── Error codes ───────────────────────────────────────────────────── */
/*                                                                       */
/* Negative = error, positive = success (byte/token count).              */
/* -1..-3 mirror jsmn; -16 and below are runtime errors.                 */

// clang-format off
enum rt_err {
    /* jsmn pass-through (keep in sync with enum jsmnerr) */
    RT_ERR_NOMEM       = -1,   /* not enough tokens                     */
    RT_ERR_JSON        = -2,   /* invalid JSON                          */
    RT_ERR_PARTIAL     = -3,   /* truncated input                       */

    /* type / structure */
    RT_ERR_TYPE        = -16,  /* token type != expected type            */
    RT_ERR_REQUIRED    = -17,  /* required field missing                 */
    RT_ERR_UNKNOWN_KEY = -18,  /* unrecognised object key (strict mode)  */

    /* value constraints */
    RT_ERR_OVERFLOW    = -32,  /* integer exceeds target range (above)   */
    RT_ERR_UNDERFLOW   = -33,  /* integer exceeds target range (below)   */
    RT_ERR_STR_LENGTH  = -34,  /* string exceeds maxLength               */
    RT_ERR_ARRAY_COUNT = -35,  /* array items exceed capacity            */
    RT_ERR_FLOAT       = -36,  /* not-finite or out-of-range float       */

    /* encode */
    RT_ERR_BUFFER      = -48,  /* output buffer too small                */
};
// clang-format on

/* ── Tagged type handle ─────────────────────────────────────────────── */
/*                                                                       */
/* uint16_t, 2-bit tag in low bits:                                      */
/*   xxxxxxxxxxxxxxx1  →  primitive     (bits[15:1] = scalar ID)         */
/*   xxxxxxxxxxxxx00   →  struct index  (bits[15:2] into rt_structs[])   */
/*   xxxxxxxxxxxxx10   →  array index   (bits[15:2] into rt_arrays[])    */

typedef uint16_t rt_type_t;

// clang-format off
#define RT_PRIM(id)     ((rt_type_t)(((id) << 1) | 1u))
#define RT_STRUCT(i)    ((rt_type_t)((i) << 2))
#define RT_ARRAY(i)     ((rt_type_t)(((i) << 2) | 2u))

#define RT_IS_PRIM(t)   ((t) & 1u)
#define RT_IS_STRUCT(t) (((t) & 3u) == 0)
#define RT_IS_ARRAY(t)  (((t) & 3u) == 2)
#define RT_PRIM_ID(t)   ((t) >> 1)
#define RT_IDX(t)       ((t) >> 2)
// clang-format on

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
    uint16_t  off_name;    // byte offset into rt_names[]
    uint16_t  off_value;   // offsetof to value
    uint16_t  off_present; // offsetof to bool present, 0xFFFF = required
    rt_type_t type;        // prim / struct idx / array idx
};

struct rt_array {
    uint8_t   kind; // RT_KIND_STRING / RT_KIND_FIXED / RT_KIND_VLA
    uint8_t   pad;
    uint16_t  max;       // capacity
    uint16_t  elem_size; // stride in bytes
    rt_type_t elem;      // element type (recursive)
};

struct rt_struct {
    uint8_t  nfields;
    uint8_t  pad;
    uint16_t size;   // sizeof(struct T)
    uint16_t ntoks;  // max jsmn tokens needed
    uint16_t field0; // start index into rt_fields[]
};

struct rt_schemas {
    const char             *names;   // field name string blob
    const struct rt_array  *arrays;  // array descriptors
    const struct rt_field  *fields;  // field descriptors
    const struct rt_struct *structs; // struct descriptors
};

#ifdef __cplusplus
extern "C" {
#endif

int
rt_decode(const struct rt_schemas *schema,
          jsmntok_t               *toks,
          uint32_t                 ntoks,
          void                    *dst,
          rt_type_t                type,
          const char              *src,
          uint32_t                 slen);

int
rt_encode(const struct rt_schemas *schemas,
          uint8_t                 *dst,
          uint32_t                 dlen,
          const void              *src,
          rt_type_t                type);

#ifdef __cplusplus
}
#endif

#endif

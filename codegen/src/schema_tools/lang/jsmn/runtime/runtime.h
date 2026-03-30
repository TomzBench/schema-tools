#ifndef SCHEMA_TOOLS_H
#define SCHEMA_TOOLS_H

#include "jsmn.h"
#include <stdbool.h>
#include <stdint.h>

/* ── Error codes ───────────────────────────────────────────────────── */
/*                                                                       */
/* Negative = error, positive = success (byte/token count).              */
/* -1..-3 mirror jsmn; -16 and below are runtime errors.                 */

// clang-format off
enum st_err {
    /* jsmn pass-through (keep in sync with enum jsmnerr) */
    ST_ERR_NOMEM       = -1,   /* not enough tokens                     */
    ST_ERR_JSON        = -2,   /* invalid JSON                          */
    ST_ERR_PARTIAL     = -3,   /* truncated input                       */

    /* type / structure */
    ST_ERR_TYPE        = -16,  /* token type != expected type            */
    ST_ERR_REQUIRED    = -17,  /* required field missing                 */
    ST_ERR_UNKNOWN_KEY = -18,  /* unrecognised object key (strict mode)  */

    /* value constraints */
    ST_ERR_OVERFLOW    = -32,  /* integer exceeds target range (above)   */
    ST_ERR_UNDERFLOW   = -33,  /* integer exceeds target range (below)   */
    ST_ERR_STR_LENGTH  = -34,  /* string exceeds maxLength               */
    ST_ERR_ARRAY_COUNT = -35,  /* array items exceed capacity            */
    ST_ERR_FLOAT       = -36,  /* not-finite or out-of-range float       */

    /* encode */
    ST_ERR_BUFFER      = -48,  /* output buffer too small                */
};
// clang-format on

/* ── Tagged type handle ─────────────────────────────────────────────── */
/*                                                                       */
/* uint16_t, 2-bit tag in low bits:                                      */
/*   xxxxxxxxxxxxxxx1  →  primitive     (bits[15:1] = scalar ID)         */
/*   xxxxxxxxxxxxx00   →  struct index  (bits[15:2] into st_structs[])   */
/*   xxxxxxxxxxxxx10   →  array index   (bits[15:2] into st_arrays[])    */

typedef uint16_t st_type_t;

// clang-format off
#define ST_PRIM(id)     ((st_type_t)(((id) << 1) | 1u))
#define ST_STRUCT(i)    ((st_type_t)((i) << 2))
#define ST_ARRAY(i)     ((st_type_t)(((i) << 2) | 2u))

#define ST_IS_PRIM(t)   ((t) & 1u)
#define ST_IS_STRUCT(t) (((t) & 3u) == 0)
#define ST_IS_ARRAY(t)  (((t) & 3u) == 2)
#define ST_PRIM_ID(t)   ((t) >> 1)
#define ST_IDX(t)       ((t) >> 2)
// clang-format on

/* ── Scalar type IDs (fit in 7 bits) ───────────────────────────────── */

// clang-format off
#define ST_KIND_BOOL   0
#define ST_KIND_CHAR   1
#define ST_KIND_U8     2
#define ST_KIND_I8     3
#define ST_KIND_U16    4
#define ST_KIND_I16    5
#define ST_KIND_U32    6
#define ST_KIND_I32    7
#define ST_KIND_U64    8
#define ST_KIND_I64    9
#define ST_KIND_FLOAT  10
#define ST_KIND_DOUBLE 11

/* Array kind IDs (only appear in st_array.kind) */
#define ST_KIND_STRING 12
#define ST_KIND_FIXED  13
#define ST_KIND_VLA    14
// clang-format on

/* ── Table entry types (8 bytes each, zero pointers) ───────────────── */

struct st_field {
    uint16_t  off_name;    // byte offset into st_names[]
    uint16_t  off_value;   // offsetof to value
    uint16_t  off_present; // offsetof to bool present, 0xFFFF = required
    st_type_t type;        // prim / struct idx / array idx
};

struct st_array {
    uint8_t   kind; // ST_KIND_STRING / ST_KIND_FIXED / ST_KIND_VLA
    uint8_t   pad;
    uint16_t  max;       // capacity
    uint16_t  elem_size; // stride in bytes
    st_type_t elem;      // element type (recursive)
};

struct st_struct {
    uint8_t  nfields;
    uint8_t  pad;
    uint16_t size;   // sizeof(struct T)
    uint16_t ntoks;  // max jsmn tokens needed
    uint16_t field0; // start index into st_fields[]
};

struct st_schemas {
    const char             *names;   // field name string blob
    const struct st_array  *arrays;  // array descriptors
    const struct st_field  *fields;  // field descriptors
    const struct st_struct *structs; // struct descriptors
};

#ifdef __cplusplus
extern "C" {
#endif

int
st_decode(const struct st_schemas *schema,
          jsmntok_t               *toks,
          uint32_t                 ntoks,
          void                    *dst,
          st_type_t                type,
          const char              *src,
          uint32_t                 slen);

int
st_encode(const struct st_schemas *schemas,
          uint8_t                 *dst,
          uint32_t                 dlen,
          const void              *src,
          st_type_t                type);

#ifdef __cplusplus
}
#endif

#endif

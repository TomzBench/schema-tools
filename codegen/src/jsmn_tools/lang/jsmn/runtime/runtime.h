#ifndef JSMN_TOOLS_H
#define JSMN_TOOLS_H

#include "jsmn.h"
#include <stdbool.h>
#include <stdint.h>

/* ── Error codes ───────────────────────────────────────────────────── */
/*                                                                       */
/* Negative = error, positive = success (byte/token count).              */
/* -1..-3 mirror jsmn; -16 and below are runtime errors.                 */

// clang-format off
enum jt_err {
    /* jsmn pass-through (keep in sync with enum jsmnerr) */
    JT_ERR_NOMEM       = -1,   /* not enough tokens                     */
    JT_ERR_JSON        = -2,   /* invalid JSON                          */
    JT_ERR_PARTIAL     = -3,   /* truncated input                       */

    /* type / structure */
    JT_ERR_TYPE        = -16,  /* token type != expected type            */
    JT_ERR_REQUIRED    = -17,  /* required field missing                 */
    JT_ERR_UNKNOWN_KEY = -18,  /* unrecognised object key (strict mode)  */

    /* value constraints */
    JT_ERR_OVERFLOW    = -32,  /* integer exceeds target range (above)   */
    JT_ERR_UNDERFLOW   = -33,  /* integer exceeds target range (below)   */
    JT_ERR_STR_LENGTH  = -34,  /* string exceeds maxLength               */
    JT_ERR_ARRAY_COUNT = -35,  /* array items exceed capacity            */
    JT_ERR_FLOAT       = -36,  /* not-finite or out-of-range float       */

    /* encode */
    JT_ERR_BUFFER      = -48,  /* output buffer too small                */
};
// clang-format on

/* ── Tagged type handle ─────────────────────────────────────────────── */
/*                                                                       */
/* uint16_t, 2-bit tag in low bits:                                      */
/*   xxxxxxxxxxxxxxx1  →  primitive     (bits[15:1] = scalar ID)         */
/*   xxxxxxxxxxxxx00   →  struct index  (bits[15:2] into jt_structs[])   */
/*   xxxxxxxxxxxxx10   →  array index   (bits[15:2] into jt_arrays[])    */

typedef uint16_t jt_type_t;

// clang-format off
#define JT_PRIM(id)     ((jt_type_t)(((id) << 1) | 1u))
#define JT_STRUCT(i)    ((jt_type_t)((i) << 2))
#define JT_ARRAY(i)     ((jt_type_t)(((i) << 2) | 2u))

#define JT_IS_PRIM(t)   ((t) & 1u)
#define JT_IS_STRUCT(t) (((t) & 3u) == 0)
#define JT_IS_ARRAY(t)  (((t) & 3u) == 2)
#define JT_PRIM_ID(t)   ((t) >> 1)
#define JT_IDX(t)       ((t) >> 2)
// clang-format on

/* ── Scalar type IDs (fit in 7 bits) ───────────────────────────────── */

// clang-format off
#define JT_KIND_BOOL   0
#define JT_KIND_CHAR   1
#define JT_KIND_U8     2
#define JT_KIND_I8     3
#define JT_KIND_U16    4
#define JT_KIND_I16    5
#define JT_KIND_U32    6
#define JT_KIND_I32    7
#define JT_KIND_U64    8
#define JT_KIND_I64    9
#define JT_KIND_FLOAT  10
#define JT_KIND_DOUBLE 11

/* Array kind IDs (only appear in jt_array.kind) */
#define JT_KIND_STRING 12
#define JT_KIND_FIXED  13
#define JT_KIND_VLA    14
// clang-format on

/* ── Table entry types (8 bytes each, zero pointers) ───────────────── */

struct jt_field {
    uint16_t  off_name;    // byte offset into jt_names[]
    uint16_t  off_value;   // offsetof to value
    uint16_t  off_present; // offsetof to bool present, 0xFFFF = required
    jt_type_t type;        // prim / struct idx / array idx
};

struct jt_array {
    uint8_t   kind; // JT_KIND_STRING / JT_KIND_FIXED / JT_KIND_VLA
    uint8_t   pad;
    uint16_t  max;       // capacity
    uint16_t  elem_size; // stride in bytes
    jt_type_t elem;      // element type (recursive)
};

struct jt_struct {
    uint8_t  nfields;
    uint8_t  pad;
    uint16_t size;   // sizeof(struct T)
    uint16_t ntoks;  // max jsmn tokens needed
    uint16_t field0; // start index into jt_fields[]
};

struct jt_schemas {
    const char             *names;   // field name string blob
    const struct jt_array  *arrays;  // array descriptors
    const struct jt_field  *fields;  // field descriptors
    const struct jt_struct *structs; // struct descriptors
};

#ifdef __cplusplus
extern "C" {
#endif

int
jt_decode(const struct jt_schemas *schema,
          jsmntok_t               *toks,
          uint32_t                 ntoks,
          void                    *dst,
          jt_type_t                type,
          const char              *src,
          uint32_t                 slen);

int
jt_encode(const struct jt_schemas *schemas,
          uint8_t                 *dst,
          uint32_t                 dlen,
          const void              *src,
          jt_type_t                type);

#ifdef __cplusplus
}
#endif

#endif

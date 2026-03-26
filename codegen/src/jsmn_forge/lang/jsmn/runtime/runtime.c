#include "runtime.h"
#include "jsmn.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#ifdef JF_HAS_FLOAT
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#endif

#ifdef JF_HAS_INT64
typedef uint64_t jf_acc_t;
typedef int64_t  jf_sacc_t;
#define JF_ACC_MAX UINT64_MAX
#else
typedef uint32_t jf_acc_t;
typedef int32_t  jf_sacc_t;
#define JF_ACC_MAX UINT32_MAX
#endif

static inline int
tok_memcmp(const char      *json,
           const jsmntok_t *tok,
           const char      *cmp,
           uint32_t         len)
{
    return tok->end - tok->start == (int)len
               ? memcmp(json + tok->start, cmp, len)
               : -1;
}

static inline int
tok_memlen(const char *json, const jsmntok_t *tok)
{
    return (uint32_t)(tok->end - tok->start);
}

static inline void
tok_memcpy(const char *json, const jsmntok_t *tok, void *dst, uint32_t len)
{
    memcpy(dst, &json[tok->start], len);
}

static int
tok_raw_int(const char *json, const jsmntok_t *tok, jf_acc_t *out, bool *neg)
{
    const char *c = &json[tok->start];
    const char *end = &json[tok->end];
    jf_acc_t    val = 0;

    *neg = false;
    if (c < end && *c == '-') {
        *neg = true;
        c++;
    }

    // Must have at least one digit
    if (c >= end || *c < '0' || *c > '9') {
        return -1;
    }

    // Reject leading zeros (JSON spec)
    if (*c == '0' && c + 1 < end && c[1] >= '0' && c[1] <= '9') {
        return -1;
    }

    while (c < end) {
        if (*c < '0' || *c > '9') {
            return -1; // non-digit -> not a pure int
        }
        jf_acc_t d = (jf_acc_t)(*c - '0');
        if (val > (JF_ACC_MAX - d) / 10) {
            return -1; // overflow
        }
        val = val * 10 + d;
        c++;
    }

    *out = val;
    return 0;
}

// clang-format off
#define JF_UINT32_TYPES(X)                     \
    X(u8,   uint8_t,   UINT8_MAX)              \
    X(u16,  uint16_t,  UINT16_MAX)             \
    X(u32,  uint32_t,  UINT32_MAX)

#define JF_INT32_TYPES(X)                      \
    X(i8,   int8_t,    INT8_MAX)               \
    X(i16,  int16_t,   INT16_MAX)              \
    X(i32,  int32_t,   INT32_MAX)

#ifdef JF_HAS_INT64
#define JF_UINT64_TYPES(X)                     \
    X(u64,  uint64_t,  UINT64_MAX)

#define JF_INT64_TYPES(X)                      \
    X(i64,  int64_t,   INT64_MAX)
#endif
// clang-format on

#define GEN_UINT_PARSER(name, ctype, hi)                                       \
    int tok_##name(const char *json, const jsmntok_t *tok, ctype *out)         \
    {                                                                          \
        jf_acc_t raw;                                                          \
        bool     neg;                                                          \
        if (tok_raw_int(json, tok, &raw, &neg))                                \
            return -1;                                                         \
        if (neg || raw > (jf_acc_t)(hi))                                       \
            return -1;                                                         \
        *out = (ctype)raw;                                                     \
        return 0;                                                              \
    }

/* Signed range check avoids implementation-defined narrowing:
 * For negative values, |v| lives in [1, MAX+1] so (raw-1) in [0, MAX].
 * Result = -(ctype)(raw-1) - 1 is always well-defined.                       */
#define GEN_INT_PARSER(name, ctype, hi)                                        \
    int tok_##name(const char *json, const jsmntok_t *tok, ctype *out)         \
    {                                                                          \
        jf_acc_t raw;                                                          \
        bool     neg;                                                          \
        if (tok_raw_int(json, tok, &raw, &neg))                                \
            return -1;                                                         \
        if (neg) {                                                             \
            if (raw == 0) {                                                    \
                *out = 0;                                                      \
                return 0;                                                      \
            }                                                                  \
            if (raw - 1 > (jf_acc_t)(hi))                                      \
                return -1;                                                     \
            *out = -(ctype)(raw - 1) - 1;                                      \
        } else {                                                               \
            if (raw > (jf_acc_t)(hi))                                          \
                return -1;                                                     \
            *out = (ctype)raw;                                                 \
        }                                                                      \
        return 0;                                                              \
    }

JF_UINT32_TYPES(GEN_UINT_PARSER)
JF_INT32_TYPES(GEN_INT_PARSER)

#ifdef JF_HAS_INT64
JF_UINT64_TYPES(GEN_UINT_PARSER)
JF_INT64_TYPES(GEN_INT_PARSER)
#endif

#undef GEN_UINT_PARSER
#undef GEN_INT_PARSER

#ifdef JF_HAS_FLOAT

// NOTE: strtod is locale-sensitive — caller must ensure LC_NUMERIC is "C".
static int
tok_raw_float(const char *json, const jsmntok_t *tok, double *out)
{
    char buf[64];
    int  len = tok->end - tok->start;
    if (len <= 0 || len >= (int)sizeof(buf)) {
        return -1;
    }
    memcpy(buf, &json[tok->start], (size_t)len);
    buf[len] = '\0';
    char *end;
    *out = strtod(buf, &end);
    if (end != &buf[len]) {
        return -1;
    }
    return 0;
}

int
tok_float(const char *json, const jsmntok_t *tok, float *out)
{
    double raw;
    if (tok_raw_float(json, tok, &raw)) {
        return -1;
    }
    if (!isfinite(raw) || raw < -(double)FLT_MAX || raw > (double)FLT_MAX) {
        return -1;
    }
    *out = (float)raw;
    return 0;
}

int
tok_double(const char *json, const jsmntok_t *tok, double *out)
{
    double raw;
    if (tok_raw_float(json, tok, &raw)) {
        return -1;
    }
    if (!isfinite(raw)) {
        return -1;
    }
    *out = raw;
    return 0;
}

#endif /* JF_HAS_FLOAT */

int
tok_bool(const char *json, const jsmntok_t *tok, bool *result)
{
    assert(tok->type == JSMN_PRIMITIVE);
    if (tok_memcmp(json, tok, "true", 4) == 0) {
        *result = true;
        return 0;
    }
    if (tok_memcmp(json, tok, "false", 5) == 0) {
        *result = false;
        return 0;
    }
    return -1;
}

int
tok_str(const char      *json,
        const jsmntok_t *tok,
        const char     **dst_p,
        uint32_t        *len)
{
    assert(tok->type == JSMN_STRING);
    uint32_t slen = (uint32_t)(tok->end - tok->start);
    if (slen <= *len) {
        *len = slen;
        *dst_p = &json[tok->start];
        return 0;
    }
    return -1;
}

bool
tok_is_null(const char *json, const jsmntok_t *tok)
{
    return tok_memcmp(json, tok, "null", 4) == 0;
}

int
tok_skip(const jsmntok_t *toks, int pos)
{
    int pending = 1;
    int i = pos;
    while (pending > 0) {
        pending--;
        if (toks[i].type == JSMN_OBJECT) {
            pending += toks[i].size * 2;
        } else if (toks[i].type == JSMN_ARRAY) {
            pending += toks[i].size;
        }
        i++;
    }
    return i - pos;
}

/* Compute element stride for arrays where elem_size==0 (inlined fixed dims) */
static uint16_t
calculate_array_stride(const struct rt_schemas *schema,
                       const struct rt_array   *a)
{
    // TODO this is able to be codegenned into the descriptors
    if (a->elem_size != 0) {
        return a->elem_size;
    } else {
        assert(RT_IS_ARRAY(a->elem));
        const struct rt_array *child = &schema->arrays[RT_IDX(a->elem)];
        return child->max * calculate_array_stride(schema, child);
    }
}

// clang-format off
#define offset_ptr(T, base, off)       ((T *)((uint8_t *)(base) + (off)))
#define offset_val(T, base, off)       (*offset_ptr(T, base, off))
#define field_is_optional(f)           ((f)->off_present != 0xFFFF)
#define field_is_present(f, base)      (offset_val(bool, base, (f)->off_present))
#define field_set_present(f, base, v)  (offset_val(bool, base, (f)->off_present) = (v))
// clang-format on

struct decoder {
    const struct rt_schemas *schemas;
    const char              *json;
    jsmntok_t               *toks;
};

static int
decode_type(const struct decoder *dec, void *dst, int itok, rt_type_t type);

static int
decode_primitive(void            *dst,
                 rt_type_t        type,
                 const char      *json,
                 const jsmntok_t *tok)
{
    switch (RT_PRIM_ID(type)) {
    case RT_KIND_BOOL:
        return tok_bool(json, tok, (bool *)dst);
    case RT_KIND_CHAR:
    case RT_KIND_U8:
        return tok_u8(json, tok, dst);
    case RT_KIND_I8:
        return tok_i8(json, tok, dst);
    case RT_KIND_U16:
        return tok_u16(json, tok, dst);
    case RT_KIND_I16:
        return tok_i16(json, tok, dst);
    case RT_KIND_U32:
        return tok_u32(json, tok, dst);
    case RT_KIND_I32:
        return tok_i32(json, tok, dst);
#ifdef JF_HAS_INT64
    case RT_KIND_U64:
        return tok_u64(json, tok, dst);
    case RT_KIND_I64:
        return tok_i64(json, tok, dst);
#endif
#ifdef JF_HAS_FLOAT
    case RT_KIND_FLOAT:
        return tok_float(json, tok, dst);
    case RT_KIND_DOUBLE:
        return tok_double(json, tok, dst);
#endif
    default:
        // Error with code generator. *Should* be impossible. Fail loudly
        assert(false);
        return -1;
    }
}

static int
decode_string(void *dst, uint32_t dlen, const char *json, jsmntok_t *tok)
{
    if (tok->type == JSMN_STRING) {
        uint32_t slen = (uint32_t)(tok->end - tok->start);
        if (slen >= dlen) {
            return RT_ERR_STR_LENGTH;
        }
        memcpy(dst, &json[tok->start], slen);
        ((uint8_t *)dst)[slen] = '\0';
        return 0;
    } else {
        return RT_ERR_TYPE;
    }
}

static int
decode_array(const struct decoder *dec, void *dst, int arr_idx, int itok)
{
    const struct rt_array *a = &dec->schemas->arrays[arr_idx];
    if (a->kind == RT_KIND_STRING) {
        return decode_string(dst, a->max, dec->json, &dec->toks[itok]);
    } else if (dec->toks[itok].type == JSMN_ARRAY) {
        // When advertised length of array exceeds max, skip the tail tokens.
        // NOTE can also perhaps be an error
        int      total = dec->toks[itok].size;
        int      count = total > a->max ? a->max : total;
        uint16_t stride = calculate_array_stride(dec->schemas, a);
        uint8_t *items = dst;
        itok++;

        if (a->kind == RT_KIND_VLA) {
            *(uint32_t *)dst = (uint32_t)count;
            items += 8;
        }

        for (int i = 0; i < count; i++) {
            void *elem = offset_ptr(void, items, (uint32_t)i * stride);
            int   err = decode_type(dec, elem, itok, a->elem);
            if (err < 0) {
                return err;
            }
            itok += tok_skip(dec->toks, itok);
        }

        return 0;
    } else {
        return RT_ERR_TYPE;
    }
}

static int
decode_struct(const struct decoder *dec, void *dst, int struct_idx, int itok)
{
    const struct rt_struct *s = &dec->schemas->structs[struct_idx];
    int                     nkeys, err = 0, n = itok;

    // Peel { token
    if (dec->toks[n].type != JSMN_OBJECT) {
        return RT_ERR_TYPE;
    }
    nkeys = dec->toks[n].size;
    n++;

    assert(s->nfields <= 64);

    // Build required mask + initialize optional presence flags
    uint64_t required = 0, seen = 0;
    for (int fidx = s->field0; fidx < s->field0 + s->nfields; fidx++) {
        const struct rt_field *f = &dec->schemas->fields[fidx];
        int                    bit = fidx - s->field0;
        if (field_is_optional(f)) {
            field_set_present(f, dst, false);
        } else {
            required |= (uint64_t)1 << bit;
        }
    }

    for (int i = 0; i < nkeys; i++) {
        // parse out key, value token
        int ktok = n;     // toks[n]   = key
        int vtok = n + 1; // toks[n+1] = value
        for (int fidx = s->field0; fidx < s->field0 + s->nfields; fidx++) {
            // get field and key
            const struct rt_field *f = &dec->schemas->fields[fidx];
            const char            *key = &dec->schemas->names[f->off_name];
            uint32_t               keylen = strlen(key);

            // If key matches field descriptor name, parse the value
            if (!tok_memcmp(dec->json, &dec->toks[ktok], key, keylen)) {
                if (field_is_optional(f)) {
                    if (tok_is_null(dec->json, &dec->toks[vtok])) {
                        field_set_present(f, dst, false);
                    } else {
                        err = decode_type(dec,
                                          offset_ptr(void, dst, f->off_value),
                                          vtok,
                                          f->type);
                        if (err < 0) {
                            return err;
                        }
                        field_set_present(f, dst, true);
                    }
                } else {
                    err = decode_type(dec,
                                      offset_ptr(void, dst, f->off_value),
                                      vtok,
                                      f->type);
                    if (err < 0) {
                        return err;
                    }
                }

                seen |= (uint64_t)1 << (fidx - s->field0);
                break;
            }
        }
        // skip key,val. ie: n++; tok_skip(toks, n);
        n += 1 + tok_skip(dec->toks, n + 1);
    }

    if ((required & ~seen) != 0) {
        return RT_ERR_REQUIRED;
    }
    return 0;
}

static int
decode_type(const struct decoder *dec, void *dst, int itok, rt_type_t type)
{
    if (RT_IS_ARRAY(type)) {
        return decode_array(dec, dst, RT_IDX(type), itok);
    } else if (RT_IS_STRUCT(type)) {
        return decode_struct(dec, dst, RT_IDX(type), itok);
    } else {
        return decode_primitive(dst, type, dec->json, &dec->toks[itok]);
    }
}

// TODO: flatten.py filters out top level arrays. we need to fix that
//       before adding top level array support.
// ie:   schema_decode_my_vla(struct my_vla*, ...)
//       schema_decode_my_arr(struct items[4], ...)
// NOTE: For top level arrays we do not use vla__{name}__n{n} convention
//       but instead use the declared name per the spec
int
rt_decode(const struct rt_schemas *schema,
          jsmntok_t               *toks,
          uint32_t                 ntoks,
          void                    *dst,
          rt_type_t                type,
          const char              *src,
          uint32_t                 slen)
{
    int         ret, atoks;
    jsmn_parser parser;

    jsmn_init(&parser);
    atoks = jsmn_parse(&parser, src, slen, toks, ntoks);
    if (atoks < 0) {
        return atoks;
    }
    if (atoks < 1) {
        return RT_ERR_PARTIAL;
    }

    struct decoder dec = {.schemas = schema, .json = src, .toks = toks};
    ret = decode_type(&dec, dst, 0, type);
    return ret < 0 ? ret : parser.pos;
}

#define cursor_push(_c, _b) ((_c)->ptr[(_c)->pos] = _b)
#define cursor_copy(_c, _b, _l) memcpy((_c)->ptr + (_c)->pos, (_b), _l)
#define cursor_push_safe(_c, _b)                                               \
    do {                                                                       \
        if ((_c)->ptr && (_c)->pos < (_c)->len) {                              \
            cursor_push(_c, _b);                                               \
            (_c)->pos++;                                                       \
        } else {                                                               \
            goto fail;                                                         \
        }                                                                      \
    } while (0)

#define cursor_copy_safe(_c, _b, _l)                                           \
    do {                                                                       \
        if ((_c)->ptr && (_c)->pos + (_l) <= (_c)->len) {                      \
            cursor_copy(_c, _b, _l);                                           \
            (_c)->pos += _l;                                                   \
        } else {                                                               \
            goto fail;                                                         \
        }                                                                      \
    } while (0)

#define cursor_init(_n, _b, _l)                                                \
    struct cursor _n = {                                                       \
        .ptr = (_b),                                                           \
        .len = (_l),                                                           \
        .pos = 0,                                                              \
    }

const char *
fmt_uint(jf_acc_t val, char (*buf)[20], uint8_t *sz)
{
    *sz = 0;
    do {
        (*buf)[20 - ++*sz] = '0' + (char)(val % 10);
        val /= 10;
    } while (val);
    return (const char *)&(*buf)[20 - *sz];
}

/* Negate without UB: -(val+1) avoids overflow at MIN, the +1 in unsigned
 * recovers the correct absolute value.  e.g. -INT32_MIN → 2147483648u.   */
const char *
fmt_int(jf_sacc_t val, char (*buf)[20], uint8_t *sz)
{
    if (val >= 0) {
        return fmt_uint((jf_acc_t)val, buf, sz);
    } else {
        const char *result = fmt_uint((jf_acc_t)(-(val + 1)) + 1, buf, sz);
        (*buf)[20 - ++*sz] = '-';
        return (const char *)&(*buf)[20 - *sz];
    }
}

struct cursor {
    uint8_t *ptr;
    uint32_t pos, len;
};

struct encoder {
    const struct rt_schemas *schemas;
    struct cursor           *cursor;
};

static int
encode_type(struct encoder *enc, void *src, rt_type_t type);

static int
encode_primitive(struct cursor *cursor,
                 rt_type_t      type,
                 const uint8_t *base,
                 uint16_t       off)
{
    uint8_t sz;
    union {
        char fmt[20];
        char snp[25];
    } tmp;
    const char *fmt;
    switch (RT_PRIM_ID(type)) {
    case RT_KIND_BOOL:
        if (offset_val(bool, base, off)) {
            cursor_copy_safe(cursor, "true", 4);
        } else {
            cursor_copy_safe(cursor, "false", 5);
        }
        break;
    case RT_KIND_CHAR:
    case RT_KIND_U8:
        fmt = fmt_uint(offset_val(const uint8_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
    case RT_KIND_I8:
        fmt = fmt_int(offset_val(const int8_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
    case RT_KIND_U16:
        fmt = fmt_uint(offset_val(const uint16_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
    case RT_KIND_I16:
        fmt = fmt_int(offset_val(const int16_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
    case RT_KIND_U32:
        fmt = fmt_uint(offset_val(const uint32_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
    case RT_KIND_I32:
        fmt = fmt_int(offset_val(const int32_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
#ifdef JF_HAS_INT64
    case RT_KIND_U64:
        fmt = fmt_uint(offset_val(const uint64_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
    case RT_KIND_I64:
        fmt = fmt_int(offset_val(const int64_t, base, off), &tmp.fmt, &sz);
        cursor_copy_safe(cursor, fmt, sz);
        break;
#endif
#ifdef JF_HAS_FLOAT
    case RT_KIND_FLOAT:

        sz = snprintf(tmp.snp,
                      sizeof(tmp),
                      "%g",
                      (double)offset_val(const float, base, off));
        assert(sz < (int)sizeof(tmp));
        cursor_copy_safe(cursor, tmp.snp, sz);
        break;
    case RT_KIND_DOUBLE:
        sz = snprintf(tmp.snp,
                      sizeof(tmp.snp),
                      "%.17g",
                      offset_val(const double, base, off));
        assert(sz < (int)sizeof(tmp.snp));
        cursor_copy_safe(cursor, tmp.snp, sz);
        break;
#endif
    }
    return (int)cursor->pos;
fail:
    return RT_ERR_BUFFER;
}

static int
encode_string(struct cursor *c, const char *src, uint32_t len)
{
    cursor_push_safe(c, '"');
    cursor_copy_safe(c, src, len);
    cursor_push_safe(c, '"');
    return c->pos;
fail:
    return RT_ERR_BUFFER;
}

static int
encode_array(struct encoder *enc, void *src, int idx)
{
    const struct rt_array *a = &enc->schemas->arrays[idx];
    if (a->kind == RT_KIND_STRING) {
        return encode_string(enc->cursor, src, strlen(src));
    } else {
        // TODO this is a compile time known attribute. ie: a->stride
        uint16_t       stride = calculate_array_stride(enc->schemas, a);
        const uint8_t *items;
        int            count;
        if (a->kind == RT_KIND_FIXED) {
            count = (int)a->max;
            items = src;
        } else {
            // We wrapped array with a length+pad prefix
            count = (int)*(const uint32_t *)src; // read length
            items = offset_ptr(void, src, 8);    // skip prefix
        }

        cursor_push_safe(enc->cursor, '[');
        for (int i = 0; i < count; i++) {
            if (i > 0) {
                cursor_push_safe(enc->cursor, ',');
            }
            int step = i * stride,
                err = encode_type(enc, offset_ptr(void, items, step), a->elem);
            if (err < 0) {
                goto fail;
            }
        }
    }
    cursor_push_safe(enc->cursor, ']');
    return enc->cursor->pos;
fail:
    return RT_ERR_BUFFER;
}

static int
encode_struct(struct encoder *enc, const void *src, int idx)
{
    const struct rt_struct *s = &enc->schemas->structs[idx];
    int                     err = -1;
    bool                    first = true;

    cursor_push_safe(enc->cursor, '{');
    for (int fidx = s->field0; fidx < s->field0 + s->nfields; fidx++) {
        const struct rt_field *f = &enc->schemas->fields[fidx];

        // Skip optional absent fields
        if (field_is_optional(f) && !field_is_present(f, src)) {
            continue;
        }

        // Add a comma when appending
        if (first) {
            first = false;
        } else {
            cursor_push_safe(enc->cursor, ',');
        }

        // "fieldname":
        cursor_push_safe(enc->cursor, '"');
        cursor_copy_safe(enc->cursor,
                         &enc->schemas->names[f->off_name],
                         strlen(&enc->schemas->names[f->off_name]));
        cursor_push_safe(enc->cursor, '"');
        cursor_push_safe(enc->cursor, ':');

        // value
        err = encode_type(enc, offset_ptr(void, src, f->off_value), f->type);
        if (err < 0) {
            goto fail;
        }
    }
    cursor_push_safe(enc->cursor, '}');
    return enc->cursor->pos;
fail:
    return RT_ERR_BUFFER;
}

static int
encode_type(struct encoder *enc, void *src, rt_type_t type)
{
    if (RT_IS_ARRAY(type)) {
        return encode_array(enc, src, RT_IDX(type));
    } else if (RT_IS_STRUCT(type)) {
        return encode_struct(enc, src, RT_IDX(type));
    } else {
        return encode_primitive(enc->cursor, type, src, 0);
    }
}

int
rt_encode_struct(const struct rt_schemas *schemas,
                 uint8_t                 *dst,
                 uint32_t                 dlen,
                 const void              *src,
                 int                      idx)
{
    struct cursor  cursor = {.ptr = dst, .pos = 0, .len = dlen};
    struct encoder enc = {.cursor = &cursor, .schemas = schemas};
    return encode_struct(&enc, src, idx);
}

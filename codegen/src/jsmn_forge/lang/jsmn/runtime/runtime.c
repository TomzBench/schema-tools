#include "runtime.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#ifdef JF_HAS_FLOAT
#include <float.h>
#include <math.h>
#include <stdlib.h>
#endif

#ifdef JF_HAS_INT64
typedef uint64_t jf_acc_t;
#define JF_ACC_MAX UINT64_MAX
#else
typedef uint32_t jf_acc_t;
#define JF_ACC_MAX UINT32_MAX
#endif

static inline int
tok_memcmp(const char *json,
           const jsmntok_t *tok,
           const char *cmp,
           uint32_t len)
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
    jf_acc_t val = 0;

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
        bool neg;                                                              \
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
        bool neg;                                                              \
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
    int len = tok->end - tok->start;
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
tok_str(const char *json,
        const jsmntok_t *tok,
        const char **dst_p,
        uint32_t *len)
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
    return tok_memcmp(json, tok, "null", 4);
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

int
rt_decode(void *dst,
          const struct rt_struct *desc,
          const char *src,
          uint32_t slen,
          jsmntok_t *toks,
          uint32_t ntoks)
{
    return -1;
}

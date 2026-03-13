/*
 * jsmn_forge.c — Table-driven JSON decode/encode runtime
 *
 * Generic decode/encode driven by const struct descriptors.
 * No codegen-specific types — only jf_struct / jf_field from the header.
 *
 * Dependencies: jsmn, <string.h>, <stdlib.h>, <stdio.h> (float only)
 */

#include "jsmn_forge.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── Private constants ───────────────────────────────────────────────── */

#define JF_MAX_FIELDS 255                       /* uint8_t nfields cap  */
#define JF_SEEN_BYTES ((JF_MAX_FIELDS + 7) / 8) /* bitset storage       */

#define JF_BIT_SET(a, i) ((a)[(i) / 8] |= (uint8_t)(1u << ((i) % 8)))
#define JF_BIT_TEST(a, i) ((a)[(i) / 8] & (1u << ((i) % 8)))

#define JF_FLOAT_BUFSZ 32  /* enough for %g of any double */
#define JF_ASCII_CTRL 0x20 /* first printable ASCII char  */

/* ═══════════════════════════════════════════════════════════════════════
 *  Token helpers
 * ═══════════════════════════════════════════════════════════════════════ */

static bool
tok_eq(const char *json, const jsmntok_t *tok, const char *key)
{
    size_t klen = strlen(key);
    return tok->type == JSMN_STRING &&
           (size_t)(tok->end - tok->start) == klen &&
           memcmp(json + tok->start, key, klen) == 0;
}

static bool
tok_is_null(const char *src, const jsmntok_t *tok)
{
    return tok->type == JSMN_PRIMITIVE && src[tok->start] == 'n';
}

static int32_t
tok_bool(const char *src, const jsmntok_t *tok, bool *out)
{
    if (tok->type != JSMN_PRIMITIVE) {
        return JF_ERR_TYPE;
    }
    char c = src[tok->start];
    if (c == 't') {
        *out = true;
    } else if (c == 'f') {
        *out = false;
    } else {
        return JF_ERR_TYPE;
    }
    return JF_OK;
}

static int32_t
tok_uint(const char *src, const jsmntok_t *tok, uint64_t *out)
{
    if (tok->type != JSMN_PRIMITIVE) {
        return JF_ERR_TYPE;
    }
    uint64_t val = 0;
    for (int i = tok->start; i < tok->end; i++) {
        char c = src[i];
        if (c < '0' || c > '9') {
            return JF_ERR_TYPE;
        }
        uint64_t d = (uint64_t)(c - '0');
        if (val > UINT64_MAX / 10) {
            return JF_ERR_OVERFLOW;
        }
        val *= 10;
        if (val > UINT64_MAX - d) {
            return JF_ERR_OVERFLOW;
        }
        val += d;
    }
    *out = val;
    return JF_OK;
}

static int32_t
tok_int(const char *src, const jsmntok_t *tok, int64_t *out)
{
    if (tok->type != JSMN_PRIMITIVE) {
        return JF_ERR_TYPE;
    }
    int i = tok->start;
    bool neg = false;
    if (i < tok->end && src[i] == '-') {
        neg = true;
        i++;
    }
    uint64_t val = 0;
    for (; i < tok->end; i++) {
        char c = src[i];
        if (c < '0' || c > '9') {
            return JF_ERR_TYPE;
        }
        uint64_t d = (uint64_t)(c - '0');
        if (val > UINT64_MAX / 10) {
            return JF_ERR_OVERFLOW;
        }
        val *= 10;
        if (val > UINT64_MAX - d) {
            return JF_ERR_OVERFLOW;
        }
        val += d;
    }
    /* INT64_MIN magnitude = INT64_MAX + 1 as uint64 */
    uint64_t mag_limit = neg ? (uint64_t)INT64_MAX + 1 : (uint64_t)INT64_MAX;
    if (val > mag_limit) {
        return JF_ERR_OVERFLOW;
    }
    *out = neg ? -(int64_t)val : (int64_t)val;
    return JF_OK;
}

static int32_t
tok_double(const char *src, const jsmntok_t *tok, double *out)
{
    if (tok->type != JSMN_PRIMITIVE) {
        return JF_ERR_TYPE;
    }
    char buf[JF_FLOAT_BUFSZ];
    int len = tok->end - tok->start;
    if (len >= (int)sizeof(buf)) {
        return JF_ERR_OVERFLOW;
    }
    memcpy(buf, src + tok->start, (size_t)len);
    buf[len] = '\0';
    char *end;
    *out = strtod(buf, &end);
    if (end == buf) {
        return JF_ERR_TYPE;
    }
    return JF_OK;
}

/* ── Range-checking helpers ─────────────────────────────────────────── */

static int32_t
check_uint_range(uint64_t v, uint8_t type)
{
    // clang-format off
    switch (type) {
    case JF_U8:  return v <= UINT8_MAX  ? JF_OK : JF_ERR_OVERFLOW;
    case JF_U16: return v <= UINT16_MAX ? JF_OK : JF_ERR_OVERFLOW;
    case JF_U32: return v <= UINT32_MAX ? JF_OK : JF_ERR_OVERFLOW;
    case JF_U64: return JF_OK;
    default:     return JF_ERR_TYPE;
    }
    // clang-format on
}

static int32_t
check_int_range(int64_t v, uint8_t type)
{
    // clang-format off
    switch (type) {
    case JF_I8:  return (v >= INT8_MIN  && v <= INT8_MAX)  ? JF_OK : JF_ERR_OVERFLOW;
    case JF_I16: return (v >= INT16_MIN && v <= INT16_MAX) ? JF_OK : JF_ERR_OVERFLOW;
    case JF_I32: return (v >= INT32_MIN && v <= INT32_MAX) ? JF_OK : JF_ERR_OVERFLOW;
    case JF_I64: return JF_OK;
    default:     return JF_ERR_TYPE;
    }
    // clang-format on
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Field helpers
 * ═══════════════════════════════════════════════════════════════════════ */

static uint16_t
elem_size(const struct jf_field *fd)
{
    // clang-format off
	switch (fd->type) {
  	case JF_BOOL:                     return (uint16_t)sizeof(bool);
  	case JF_U8:  case JF_I8:          return 1;
  	case JF_U16: case JF_I16:         return 2;
  	case JF_U32: case JF_I32:         return 4;
  	case JF_U64: case JF_I64:         return 8;
  	case JF_FLOAT:                    return (uint16_t)sizeof(float);
  	case JF_DOUBLE:                   return (uint16_t)sizeof(double);
  	case JF_STRING:                   return fd->count;
  	case JF_OBJECT:                   return fd->child ? fd->child->size : 0;
  	default:                          return 0;
  	}
    // clang-format on
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Decode: value extraction
 * ═══════════════════════════════════════════════════════════════════════ */

/* Parse unsigned token and cast-store into the correctly-sized slot. */
static int32_t
decode_unsigned(void *slot, uint8_t type, const char *src, const jsmntok_t *tok)
{
    uint64_t v;
    int32_t rc = tok_uint(src, tok, &v);
    if (rc < 0) {
        return rc;
    }
    rc = check_uint_range(v, type);
    if (rc < 0) {
        return rc;
    }
    // clang-format off
	switch (type) {
  	case JF_U8:  *(uint8_t *)slot  = (uint8_t)v;   break;
  	case JF_U16: *(uint16_t *)slot = (uint16_t)v;  break;
  	case JF_U32: *(uint32_t *)slot = (uint32_t)v;  break;
  	case JF_U64: *(uint64_t *)slot = v;            break;
  	default:                                       break;
  	}
    // clang-format on
    return JF_OK;
}

/* Parse signed token and cast-store into the correctly-sized slot. */
static int32_t
decode_signed(void *slot, uint8_t type, const char *src, const jsmntok_t *tok)
{
    int64_t v;
    int32_t rc = tok_int(src, tok, &v);
    if (rc < 0) {
        return rc;
    }
    rc = check_int_range(v, type);
    if (rc < 0) {
        return rc;
    }
    // clang-format off
	switch (type) {
  	case JF_I8:  *(int8_t *)slot  = (int8_t)v;  break;
  	case JF_I16: *(int16_t *)slot = (int16_t)v; break;
  	case JF_I32: *(int32_t *)slot = (int32_t)v; break;
  	case JF_I64: *(int64_t *)slot = v;          break;
  	default:                                    break;
  	}
    // clang-format on
    return JF_OK;
}

/* Decode a single scalar value at toks[pos] into slot.
 * Returns JF_OK or negative JF_ERR_*. */
static int32_t
decode_value(void *slot,
             const struct jf_field *fd,
             const char *src,
             const jsmntok_t *toks,
             int pos)
{
    const jsmntok_t *tok = &toks[pos];
    int32_t rc;

    switch (fd->type) {
    case JF_BOOL:
        return tok_bool(src, tok, (bool *)slot);

    case JF_U8:
    case JF_U16:
    case JF_U32:
    case JF_U64:
        return decode_unsigned(slot, fd->type, src, tok);
    case JF_I8:
    case JF_I16:
    case JF_I32:
    case JF_I64:
        return decode_signed(slot, fd->type, src, tok);

    case JF_FLOAT: {
        double v;
        rc = tok_double(src, tok, &v);
        if (rc < 0) {
            return rc;
        }
        *(float *)slot = (float)v;
        return JF_OK;
    }
    case JF_DOUBLE: {
        double v;
        rc = tok_double(src, tok, &v);
        if (rc < 0) {
            return rc;
        }
        *(double *)slot = v;
        return JF_OK;
    }
    case JF_STRING: {
        if (tok->type != JSMN_STRING) {
            return JF_ERR_TYPE;
        }
        uint32_t len = (uint32_t)(tok->end - tok->start);
        if (len >= fd->count) {
            return JF_ERR_OVERFLOW;
        }
        memcpy(slot, src + tok->start, len);
        ((uint8_t *)slot)[len] = '\0';
        return JF_OK;
    }
    case JF_OBJECT: {
        if (!fd->child) {
            return JF_ERR_TYPE;
        }
        rc = jf_decode_object(slot, fd->child, src, toks, pos);
        return rc < 0 ? rc : JF_OK;
    }
    default:
        return JF_ERR_TYPE;
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Decode: arrays
 * ═══════════════════════════════════════════════════════════════════════ */

/* Returns element count on success, negative JF_ERR_* on failure. */
static int32_t
decode_array(void *base,
             const struct jf_field *fd,
             const char *src,
             const jsmntok_t *toks,
             int pos)
{
    if (toks[pos].type != JSMN_ARRAY) {
        return JF_ERR_TYPE;
    }
    uint32_t n = (uint32_t)toks[pos].size;

    if (fd->flags & JF_F_ARRAY) {
        if (n != fd->count) {
            return JF_ERR_OVERFLOW;
        }
    } else {
        if (n > fd->count) {
            return JF_ERR_OVERFLOW;
        }
    }

    uint16_t stride = elem_size(fd);
    int elem_pos = pos + 1;
    for (uint32_t i = 0; i < n; i++) {
        void *slot = (uint8_t *)base + i * stride;
        int32_t rc = decode_value(slot, fd, src, toks, elem_pos);
        if (rc < 0) {
            return rc;
        }
        elem_pos += jf_tok_skip(toks, elem_pos);
    }
    return (int32_t)n;
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Public: Decode
 * ═══════════════════════════════════════════════════════════════════════ */

int32_t
jf_decode_object(void *dst,
                 const struct jf_struct *desc,
                 const char *src,
                 const jsmntok_t *toks,
                 int pos)
{
    if (toks[pos].type != JSMN_OBJECT) {
        return JF_ERR_TYPE;
    }

    memset(dst, 0, desc->size);

    /* Bit per field — tracks which fields were decoded */
    uint8_t seen[JF_SEEN_BYTES];
    memset(seen, 0, sizeof(seen));

    int nkeys = toks[pos].size;
    int i = pos + 1;

    for (int k = 0; k < nkeys; k++) {
        const jsmntok_t *key = &toks[i];
        int val_pos = i + 1;

        for (uint8_t f = 0; f < desc->nfields; f++) {
            const struct jf_field *fd = &desc->fields[f];
            if (!tok_eq(src, key, fd->name)) {
                continue;
            }

            uint8_t *base = (uint8_t *)dst;

            /* JSON null */
            if (tok_is_null(src, &toks[val_pos])) {
                if (!(fd->flags & JF_F_OPTIONAL)) {
                    return JF_ERR_TYPE;
                }
                /* leave present = false (already zeroed) */
                JF_BIT_SET(seen, f);
                break;
            }

            /* Set presence flag */
            if (fd->flags & JF_F_OPTIONAL) {
                *(bool *)(base + fd->present) = true;
            }

            int32_t rc;
            if (fd->flags & (JF_F_ARRAY | JF_F_VLA)) {
                rc = decode_array(base + fd->offset, fd, src, toks, val_pos);
                if (rc < 0) {
                    return rc;
                }
                if (fd->flags & JF_F_VLA) {
                    *(uint32_t *)(base + fd->len_offset) = (uint32_t)rc;
                }
            } else {
                rc = decode_value(base + fd->offset, fd, src, toks, val_pos);
                if (rc < 0) {
                    return rc;
                }
            }

            JF_BIT_SET(seen, f);
            break;
        }

        /* Advance past key + value */
        i = val_pos + jf_tok_skip(toks, val_pos);
    }

    /* Verify required fields */
    for (uint8_t f = 0; f < desc->nfields; f++) {
        if (desc->fields[f].flags & JF_F_OPTIONAL) {
            continue;
        }
        if (!JF_BIT_TEST(seen, f)) {
            return JF_ERR_REQUIRED;
        }
    }

    return jf_tok_skip(toks, pos);
}

int32_t
jf_decode(void *dst,
          const struct jf_struct *desc,
          const char *src,
          uint32_t slen,
          jsmntok_t *toks,
          uint32_t ntoks)
{
    jsmn_parser parser;
    jsmn_init(&parser);
    int r = jsmn_parse(&parser, src, (size_t)slen, toks, ntoks);
    if (r < 0) {
        return JF_ERR_PARSE;
    }
    if (r < 1) {
        return JF_ERR_TYPE;
    }

    int32_t consumed = jf_decode_object(dst, desc, src, toks, 0);
    return consumed < 0 ? consumed : JF_OK;
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Encode: emission helpers
 * ═══════════════════════════════════════════════════════════════════════ */

static const char hex_lut[] = "0123456789abcdef";

static int32_t
emit_uint(uint8_t *dst, uint32_t dlen, uint64_t val)
{
    char buf[21]; /* max uint64: 20 digits + NUL */
    int i = (int)sizeof(buf) - 1;
    buf[i] = '\0';
    do {
        buf[--i] = '0' + (char)(val % 10);
        val /= 10;
    } while (val);
    uint32_t len = (uint32_t)((int)sizeof(buf) - 1 - i);
    if (len > dlen) {
        return JF_ERR_BUFFER;
    }
    memcpy(dst, buf + i, len);
    return (int32_t)len;
}

static int32_t
emit_int(uint8_t *dst, uint32_t dlen, int64_t val)
{
    if (val >= 0) {
        return emit_uint(dst, dlen, (uint64_t)val);
    }
    if (dlen < 1) {
        return JF_ERR_BUFFER;
    }
    dst[0] = '-';
    /* (uint64_t)0 - (uint64_t)val avoids signed overflow UB on INT64_MIN */
    int32_t r = emit_uint(dst + 1, dlen - 1, (uint64_t)0 - (uint64_t)val);
    return r < 0 ? r : r + 1;
}

static int32_t
emit_str(uint8_t *dst, uint32_t dlen, const uint8_t *str, uint16_t maxlen)
{
    uint32_t n = 0;
    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n++] = '"';

    const uint8_t *end = str + maxlen;
    for (; str < end && *str; str++) {
        uint8_t c = *str;
        if (c == '"' || c == '\\') {
            if (n + 2 > dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = '\\';
            dst[n++] = c;
        } else if (c == '\n') {
            if (n + 2 > dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = '\\';
            dst[n++] = 'n';
        } else if (c == '\r') {
            if (n + 2 > dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = '\\';
            dst[n++] = 'r';
        } else if (c == '\t') {
            if (n + 2 > dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = '\\';
            dst[n++] = 't';
        } else if (c < JF_ASCII_CTRL) {
            if (n + 6 > dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = '\\';
            dst[n++] = 'u';
            dst[n++] = '0';
            dst[n++] = '0';
            dst[n++] = (uint8_t)hex_lut[(c >> 4) & 0xf];
            dst[n++] = (uint8_t)hex_lut[c & 0xf];
        } else {
            if (n >= dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = c;
        }
    }

    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n++] = '"';
    return (int32_t)n;
}

static int32_t
emit_key(uint8_t *dst, uint32_t dlen, const char *name)
{
    /* Keys are known strings from descriptors — no escaping needed */
    uint32_t klen = (uint32_t)strlen(name);
    /* "key": → open quote + key + close quote + colon */
    uint32_t need = 1 + klen + 1 + 1;
    if (need > dlen) {
        return JF_ERR_BUFFER;
    }
    dst[0] = '"';
    memcpy(dst + 1, name, klen);
    dst[klen + 1] = '"';
    dst[klen + 2] = ':';
    return (int32_t)need;
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Encode: value / array
 * ═══════════════════════════════════════════════════════════════════════ */

static int32_t
encode_value(uint8_t *dst,
             uint32_t dlen,
             const void *slot,
             const struct jf_field *fd)
{
    switch (fd->type) {
    case JF_BOOL: {
        const char *s = *(const bool *)slot ? "true" : "false";
        uint32_t len = *(const bool *)slot ? 4 : 5;
        if (len > dlen) {
            return JF_ERR_BUFFER;
        }
        memcpy(dst, s, len);
        return (int32_t)len;
    }
    case JF_U8:
        return emit_uint(dst, dlen, *(const uint8_t *)slot);
    case JF_I8:
        return emit_int(dst, dlen, *(const int8_t *)slot);
    case JF_U16:
        return emit_uint(dst, dlen, *(const uint16_t *)slot);
    case JF_I16:
        return emit_int(dst, dlen, *(const int16_t *)slot);
    case JF_U32:
        return emit_uint(dst, dlen, *(const uint32_t *)slot);
    case JF_I32:
        return emit_int(dst, dlen, *(const int32_t *)slot);
    case JF_U64:
        return emit_uint(dst, dlen, *(const uint64_t *)slot);
    case JF_I64:
        return emit_int(dst, dlen, *(const int64_t *)slot);
    case JF_FLOAT: {
        int n = snprintf((char *)dst, dlen, "%g", (double)*(const float *)slot);
        if (n < 0 || (uint32_t)n >= dlen) {
            return JF_ERR_BUFFER;
        }
        return n;
    }
    case JF_DOUBLE: {
        int n = snprintf((char *)dst, dlen, "%g", *(const double *)slot);
        if (n < 0 || (uint32_t)n >= dlen) {
            return JF_ERR_BUFFER;
        }
        return n;
    }
    case JF_STRING:
        return emit_str(dst, dlen, (const uint8_t *)slot, fd->count);
    case JF_OBJECT:
        if (!fd->child) {
            return JF_ERR_TYPE;
        }
        return jf_encode(dst, dlen, slot, fd->child);
    default:
        return JF_ERR_TYPE;
    }
}

static int32_t
encode_array(uint8_t *dst,
             uint32_t dlen,
             const void *base,
             const struct jf_field *fd,
             uint32_t count)
{
    uint32_t n = 0;
    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n++] = '[';

    uint16_t stride = elem_size(fd);
    for (uint32_t i = 0; i < count; i++) {
        if (i > 0) {
            if (n >= dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = ',';
        }
        const void *elem = (const uint8_t *)base + i * stride;
        int32_t w = encode_value(dst + n, dlen - n, elem, fd);
        if (w < 0) {
            return w;
        }
        n += (uint32_t)w;
    }

    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n++] = ']';
    return (int32_t)n;
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Public: Encode
 * ═══════════════════════════════════════════════════════════════════════ */

int32_t
jf_encode(uint8_t *dst,
          uint32_t dlen,
          const void *src,
          const struct jf_struct *desc)
{
    uint32_t n = 0;
    int32_t w;
    bool first = true;

    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n++] = '{';

    for (uint8_t f = 0; f < desc->nfields; f++) {
        const struct jf_field *fd = &desc->fields[f];
        const uint8_t *base = (const uint8_t *)src;

        /* Skip absent optional fields */
        if ((fd->flags & JF_F_OPTIONAL) &&
            !*(const bool *)(base + fd->present)) {
            continue;
        }

        if (!first) {
            if (n >= dlen) {
                return JF_ERR_BUFFER;
            }
            dst[n++] = ',';
        }
        first = false;

        /* Key */
        w = emit_key(dst + n, dlen - n, fd->name);
        if (w < 0) {
            return w;
        }
        n += (uint32_t)w;

        /* Value */
        if (fd->flags & (JF_F_ARRAY | JF_F_VLA)) {
            uint32_t count;
            if (fd->flags & JF_F_VLA) {
                count = *(const uint32_t *)(base + fd->len_offset);
            } else {
                count = fd->count;
            }
            w = encode_array(dst + n, dlen - n, base + fd->offset, fd, count);
        } else {
            w = encode_value(dst + n, dlen - n, base + fd->offset, fd);
        }
        if (w < 0) {
            return w;
        }
        n += (uint32_t)w;
    }

    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n++] = '}';

    /* Null-terminate */
    if (n >= dlen) {
        return JF_ERR_BUFFER;
    }
    dst[n] = '\0';

    return (int32_t)n;
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Length computation (mirrors encode logic, counts bytes)
 * ═══════════════════════════════════════════════════════════════════════ */

static uint32_t
len_str(const uint8_t *str, uint16_t maxlen)
{
    uint32_t n = 2; /* quotes */
    const uint8_t *end = str + maxlen;
    for (; str < end && *str; str++) {
        uint8_t c = *str;
        if (c == '"' || c == '\\' || c == '\n' || c == '\r' || c == '\t') {
            n += 2;
        } else if (c < JF_ASCII_CTRL) {
            n += 6;
        } else {
            n += 1;
        }
    }
    return n;
}

static uint32_t
len_uint(uint64_t val)
{
    uint32_t n = 0;
    do {
        n++;
        val /= 10;
    } while (val);
    return n;
}

static uint32_t
len_int(int64_t val)
{
    if (val >= 0) {
        return len_uint((uint64_t)val);
    }
    return 1 + len_uint((uint64_t)0 - (uint64_t)val);
}

static uint32_t
len_value(const void *slot, const struct jf_field *fd)
{
    switch (fd->type) {
    case JF_BOOL:
        return *(const bool *)slot ? 4 : 5;
    case JF_U8:
        return len_uint(*(const uint8_t *)slot);
    case JF_I8:
        return len_int(*(const int8_t *)slot);
    case JF_U16:
        return len_uint(*(const uint16_t *)slot);
    case JF_I16:
        return len_int(*(const int16_t *)slot);
    case JF_U32:
        return len_uint(*(const uint32_t *)slot);
    case JF_I32:
        return len_int(*(const int32_t *)slot);
    case JF_U64:
        return len_uint(*(const uint64_t *)slot);
    case JF_I64:
        return len_int(*(const int64_t *)slot);
    case JF_FLOAT: {
        char buf[JF_FLOAT_BUFSZ];
        int n = snprintf(buf, sizeof(buf), "%g", (double)*(const float *)slot);
        return n > 0 ? (uint32_t)n : 1;
    }
    case JF_DOUBLE: {
        char buf[JF_FLOAT_BUFSZ];
        int n = snprintf(buf, sizeof(buf), "%g", *(const double *)slot);
        return n > 0 ? (uint32_t)n : 1;
    }
    case JF_STRING:
        return len_str((const uint8_t *)slot, fd->count);
    case JF_OBJECT:
        return fd->child ? jf_len(slot, fd->child) : 0;
    default:
        return 0;
    }
}

static uint32_t
len_array(const void *base, const struct jf_field *fd, uint32_t count)
{
    uint32_t n = 2; /* [] */
    if (count > 1) {
        n += count - 1; /* commas */
    }
    uint16_t stride = elem_size(fd);
    for (uint32_t i = 0; i < count; i++) {
        const void *elem = (const uint8_t *)base + i * stride;
        n += len_value(elem, fd);
    }
    return n;
}

uint32_t
jf_len(const void *src, const struct jf_struct *desc)
{
    uint32_t n = 2; /* {} */
    bool first = true;

    for (uint8_t f = 0; f < desc->nfields; f++) {
        const struct jf_field *fd = &desc->fields[f];
        const uint8_t *base = (const uint8_t *)src;

        if ((fd->flags & JF_F_OPTIONAL) &&
            !*(const bool *)(base + fd->present)) {
            continue;
        }

        if (!first) {
            n += 1; /* comma */
        }
        first = false;

        /* "name": → open quote + name + close quote + colon */
        n += 1 + (uint32_t)strlen(fd->name) + 1 + 1;

        /* Value */
        if (fd->flags & (JF_F_ARRAY | JF_F_VLA)) {
            uint32_t count;
            if (fd->flags & JF_F_VLA) {
                count = *(const uint32_t *)(base + fd->len_offset);
            } else {
                count = fd->count;
            }
            n += len_array(base + fd->offset, fd, count);
        } else {
            n += len_value(base + fd->offset, fd);
        }
    }

    return n;
}

/* ═══════════════════════════════════════════════════════════════════════
 *  Public: Utilities
 * ═══════════════════════════════════════════════════════════════════════ */

int
jf_tok_skip(const jsmntok_t *toks, int pos)
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

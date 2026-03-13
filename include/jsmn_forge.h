/*
 * jsmn_forge.h — Table-driven JSON decode/encode for C structs
 *
 * This library provides generic decode/encode functions driven by struct
 * descriptors. Codegen produces the descriptors (const data in .rodata);
 * this library provides the runtime logic (~1.5–2 KB .text).
 *
 * Dependencies: jsmn.h
 *
 * Usage (with codegen-generated descriptors):
 *
 *     jsmntok_t toks[DEVICE_INFO_NTOKS];
 *     struct device_info info;
 *     int32_t rc = jf_decode(&info, &device_info_desc,
 *                            json, json_len, toks, DEVICE_INFO_NTOKS);
 *
 * Or with the codegen convenience wrapper:
 *
 *     struct device_info info;
 *     int32_t rc = decode_device_info(&info, json, json_len);
 */

#ifndef JSMN_FORGE_H
#define JSMN_FORGE_H

#include "jsmn.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Error codes ─────────────────────────────────────────────────────── */

#define JF_OK 0
#define JF_ERR_PARSE -1    /* jsmn tokenization failed                 */
#define JF_ERR_TYPE -2     /* unexpected JSON value type                */
#define JF_ERR_REQUIRED -3 /* required field missing in JSON            */
#define JF_ERR_OVERFLOW -4 /* string exceeds maxLength / array capacity */
#define JF_ERR_BUFFER -5   /* encode output buffer too small            */

/* ── Type tags ───────────────────────────────────────────────────────── */
/*                                                                        */
/* Element type for the field value. For arrays (JF_F_ARRAY / JF_F_VLA), */
/* this is the element type, not the container type.                      */

// clang-format off
enum jf_type {
    JF_BOOL,
    JF_U8,    JF_I8,
    JF_U16,   JF_I16,
    JF_U32,   JF_I32,
    JF_U64,   JF_I64,
    JF_FLOAT, JF_DOUBLE,
    JF_STRING,               /* null-terminated uint8_t[count]            */
    JF_OBJECT,               /* nested struct — see field.child           */
};
// clang-format on

/* ── Field flags ─────────────────────────────────────────────────────── */

#define JF_F_OPTIONAL (1 << 0) /* has bool present flag                */
#define JF_F_ARRAY (1 << 1)    /* fixed-size array T[count]            */
#define JF_F_VLA (1 << 2)      /* VLA wrapper: { uint32_t len; T[]; }  */

/* ── Descriptors ─────────────────────────────────────────────────────── */
/*                                                                        */
/* Codegen populates these as const data. The library reads them at       */
/* runtime to drive generic decode/encode logic.                          */
/*                                                                        */
/* Offset fields use offsetof() values computed by codegen. For optional  */
/* fields, `offset` points to the value storage inside the optional       */
/* wrapper and `present` points to the bool flag. For VLA fields,         */
/* `offset` points to the items array and `len_offset` points to the     */
/* uint32_t length counter. When a flag is absent, its corresponding     */
/* offset field is unused.                                                */

struct jf_struct;

struct jf_field {
  const char *name;              /* JSON key (null-terminated)    */
  const struct jf_struct *child; /* nested descriptor (JF_OBJECT) */
  uint16_t offset;               /* byte offset to value / items  */
  uint16_t present;              /* byte offset to bool present   */
  uint16_t len_offset;           /* byte offset to uint32_t len   */
  uint16_t count;                /* maxLength (string) or         */
                                 /* capacity (array / VLA)        */
  uint8_t type;                  /* enum jf_type                  */
  uint8_t flags;                 /* JF_F_* bitmask                */
};

struct jf_struct {
  const struct jf_field *fields;
  uint16_t size;   /* sizeof(struct T)              */
  uint16_t ntoks;  /* max jsmn tokens needed        */
  uint8_t nfields; /* number of fields              */
  uint8_t pad[3];
};

/* ── Decode ──────────────────────────────────────────────────────────── */

/*
 * Parse JSON string and decode into dst struct.
 *
 * Caller provides a jsmntok_t buffer (stack or static). Use desc->ntoks
 * for the required size. Codegen emits a per-type NTOKS constant.
 *
 * Returns JF_OK on success, negative JF_ERR_* on failure.
 */
int32_t
jf_decode(void *dst,
          const struct jf_struct *desc,
          const char *src,
          uint32_t slen,
          jsmntok_t *toks,
          uint32_t ntoks);

/*
 * Decode an object from a pre-parsed token array starting at toks[pos].
 *
 * Used internally for nested objects. Exposed for callers who parse once
 * and decode multiple objects from the same token array.
 *
 * Returns number of tokens consumed on success, negative JF_ERR_* on
 * failure.
 */
int32_t
jf_decode_object(void *dst,
                 const struct jf_struct *desc,
                 const char *src,
                 const jsmntok_t *toks,
                 int pos);

/* ── Encode ──────────────────────────────────────────────────────────── */

/*
 * Encode struct as JSON into dst buffer.
 *
 * Output is null-terminated. Returns bytes written (excluding NUL) on
 * success, negative JF_ERR_* on failure.
 */
int32_t
jf_encode(uint8_t *dst,
          uint32_t dlen,
          const void *src,
          const struct jf_struct *desc);

/*
 * Compute encoded JSON length for this instance.
 *
 * Inspects optional presence flags to compute actual (not worst-case)
 * length. Add 1 for the null terminator when allocating a buffer.
 */
uint32_t
jf_len(const void *src, const struct jf_struct *desc);

/* ── Utilities ───────────────────────────────────────────────────────── */

/*
 * Count tokens to skip past value at toks[pos] (including itself).
 *
 * Useful for walking token arrays or skipping unknown fields in custom
 * decode logic layered on top of jf_decode.
 */
int
jf_tok_skip(const jsmntok_t *toks, int pos);

#ifdef __cplusplus
}
#endif

#endif /* JSMN_FORGE_H */

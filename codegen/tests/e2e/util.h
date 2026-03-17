/**
 * util.h — test utilities for e2e tests
 *
 * VLA(n, ...)              VLA struct initializer shorthand
 * ARRAY_SIZE(arr)          Compile-time array length
 * LISTIFY(N, F, sep, ...)  Repeat F(idx, ...) N times (max 64)
 */
#ifndef UTIL_H
#define UTIL_H

/* ── VLA initializer ─────────────────────────────────────────────────
 *
 *   VLA(3, 1, 2, 3)
 *     => {.len = 3, .items = {1, 2, 3}}
 *
 *   VLA(2, VLA(3, 1, 2, 3), VLA(3, 4, 5, 6))
 *     => nested VLA-of-VLA initializer
 */
#define VLA(n, ...)                                                            \
    {                                                                          \
        .len = (n), .items = { __VA_ARGS__ }                                   \
    }

/* ── Array size ──────────────────────────────────────────────────── */
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

/* ── LISTIFY ─────────────────────────────────────────────────────── */
#include "listify.h"

#endif /* UTIL_H */

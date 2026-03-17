/**
 * listify.h — LISTIFY(N, F, sep, ...) macro for e2e tests
 *
 * Repeats F(idx, ...) N times with separator, supporting 0..64.
 *
 * Usage:
 *   #define POINT(idx, _) {.x = idx, .y = idx * 10}
 *   struct point arr[4] = { LISTIFY(4, POINT, (, )) };
 *
 *   #define ROW(idx, _) VLA(3, idx*3+1, idx*3+2, idx*3+3)
 *   struct vla mat = VLA(4, LISTIFY(4, ROW, (, )));
 */
#ifndef LISTIFY_H
#define LISTIFY_H

#define Z_CAT(a, b) a##b
#define LISTIFY(N, F, sep, ...) Z_CAT(Z_LISTIFY_, N)(F, sep, __VA_ARGS__)

// clang-format off
#define Z_LISTIFY_0(F, sep, ...)
#define Z_LISTIFY_1(F, sep, ...) \
    F(0, __VA_ARGS__)
#define Z_LISTIFY_2(F, sep, ...) \
    Z_LISTIFY_1(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(1, __VA_ARGS__)
#define Z_LISTIFY_3(F, sep, ...) \
    Z_LISTIFY_2(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(2, __VA_ARGS__)
#define Z_LISTIFY_4(F, sep, ...) \
    Z_LISTIFY_3(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(3, __VA_ARGS__)
#define Z_LISTIFY_5(F, sep, ...) \
    Z_LISTIFY_4(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(4, __VA_ARGS__)
#define Z_LISTIFY_6(F, sep, ...) \
    Z_LISTIFY_5(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(5, __VA_ARGS__)
#define Z_LISTIFY_7(F, sep, ...) \
    Z_LISTIFY_6(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(6, __VA_ARGS__)
#define Z_LISTIFY_8(F, sep, ...) \
    Z_LISTIFY_7(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(7, __VA_ARGS__)
#define Z_LISTIFY_9(F, sep, ...) \
    Z_LISTIFY_8(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(8, __VA_ARGS__)
#define Z_LISTIFY_10(F, sep, ...) \
    Z_LISTIFY_9(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(9, __VA_ARGS__)
#define Z_LISTIFY_11(F, sep, ...) \
    Z_LISTIFY_10(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(10, __VA_ARGS__)
#define Z_LISTIFY_12(F, sep, ...) \
    Z_LISTIFY_11(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(11, __VA_ARGS__)
#define Z_LISTIFY_13(F, sep, ...) \
    Z_LISTIFY_12(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(12, __VA_ARGS__)
#define Z_LISTIFY_14(F, sep, ...) \
    Z_LISTIFY_13(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(13, __VA_ARGS__)
#define Z_LISTIFY_15(F, sep, ...) \
    Z_LISTIFY_14(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(14, __VA_ARGS__)
#define Z_LISTIFY_16(F, sep, ...) \
    Z_LISTIFY_15(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(15, __VA_ARGS__)
#define Z_LISTIFY_17(F, sep, ...) \
    Z_LISTIFY_16(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(16, __VA_ARGS__)
#define Z_LISTIFY_18(F, sep, ...) \
    Z_LISTIFY_17(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(17, __VA_ARGS__)
#define Z_LISTIFY_19(F, sep, ...) \
    Z_LISTIFY_18(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(18, __VA_ARGS__)
#define Z_LISTIFY_20(F, sep, ...) \
    Z_LISTIFY_19(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(19, __VA_ARGS__)
#define Z_LISTIFY_21(F, sep, ...) \
    Z_LISTIFY_20(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(20, __VA_ARGS__)
#define Z_LISTIFY_22(F, sep, ...) \
    Z_LISTIFY_21(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(21, __VA_ARGS__)
#define Z_LISTIFY_23(F, sep, ...) \
    Z_LISTIFY_22(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(22, __VA_ARGS__)
#define Z_LISTIFY_24(F, sep, ...) \
    Z_LISTIFY_23(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(23, __VA_ARGS__)
#define Z_LISTIFY_25(F, sep, ...) \
    Z_LISTIFY_24(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(24, __VA_ARGS__)
#define Z_LISTIFY_26(F, sep, ...) \
    Z_LISTIFY_25(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(25, __VA_ARGS__)
#define Z_LISTIFY_27(F, sep, ...) \
    Z_LISTIFY_26(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(26, __VA_ARGS__)
#define Z_LISTIFY_28(F, sep, ...) \
    Z_LISTIFY_27(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(27, __VA_ARGS__)
#define Z_LISTIFY_29(F, sep, ...) \
    Z_LISTIFY_28(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(28, __VA_ARGS__)
#define Z_LISTIFY_30(F, sep, ...) \
    Z_LISTIFY_29(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(29, __VA_ARGS__)
#define Z_LISTIFY_31(F, sep, ...) \
    Z_LISTIFY_30(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(30, __VA_ARGS__)
#define Z_LISTIFY_32(F, sep, ...) \
    Z_LISTIFY_31(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(31, __VA_ARGS__)
#define Z_LISTIFY_33(F, sep, ...) \
    Z_LISTIFY_32(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(32, __VA_ARGS__)
#define Z_LISTIFY_34(F, sep, ...) \
    Z_LISTIFY_33(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(33, __VA_ARGS__)
#define Z_LISTIFY_35(F, sep, ...) \
    Z_LISTIFY_34(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(34, __VA_ARGS__)
#define Z_LISTIFY_36(F, sep, ...) \
    Z_LISTIFY_35(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(35, __VA_ARGS__)
#define Z_LISTIFY_37(F, sep, ...) \
    Z_LISTIFY_36(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(36, __VA_ARGS__)
#define Z_LISTIFY_38(F, sep, ...) \
    Z_LISTIFY_37(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(37, __VA_ARGS__)
#define Z_LISTIFY_39(F, sep, ...) \
    Z_LISTIFY_38(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(38, __VA_ARGS__)
#define Z_LISTIFY_40(F, sep, ...) \
    Z_LISTIFY_39(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(39, __VA_ARGS__)
#define Z_LISTIFY_41(F, sep, ...) \
    Z_LISTIFY_40(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(40, __VA_ARGS__)
#define Z_LISTIFY_42(F, sep, ...) \
    Z_LISTIFY_41(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(41, __VA_ARGS__)
#define Z_LISTIFY_43(F, sep, ...) \
    Z_LISTIFY_42(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(42, __VA_ARGS__)
#define Z_LISTIFY_44(F, sep, ...) \
    Z_LISTIFY_43(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(43, __VA_ARGS__)
#define Z_LISTIFY_45(F, sep, ...) \
    Z_LISTIFY_44(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(44, __VA_ARGS__)
#define Z_LISTIFY_46(F, sep, ...) \
    Z_LISTIFY_45(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(45, __VA_ARGS__)
#define Z_LISTIFY_47(F, sep, ...) \
    Z_LISTIFY_46(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(46, __VA_ARGS__)
#define Z_LISTIFY_48(F, sep, ...) \
    Z_LISTIFY_47(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(47, __VA_ARGS__)
#define Z_LISTIFY_49(F, sep, ...) \
    Z_LISTIFY_48(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(48, __VA_ARGS__)
#define Z_LISTIFY_50(F, sep, ...) \
    Z_LISTIFY_49(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(49, __VA_ARGS__)
#define Z_LISTIFY_51(F, sep, ...) \
    Z_LISTIFY_50(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(50, __VA_ARGS__)
#define Z_LISTIFY_52(F, sep, ...) \
    Z_LISTIFY_51(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(51, __VA_ARGS__)
#define Z_LISTIFY_53(F, sep, ...) \
    Z_LISTIFY_52(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(52, __VA_ARGS__)
#define Z_LISTIFY_54(F, sep, ...) \
    Z_LISTIFY_53(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(53, __VA_ARGS__)
#define Z_LISTIFY_55(F, sep, ...) \
    Z_LISTIFY_54(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(54, __VA_ARGS__)
#define Z_LISTIFY_56(F, sep, ...) \
    Z_LISTIFY_55(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(55, __VA_ARGS__)
#define Z_LISTIFY_57(F, sep, ...) \
    Z_LISTIFY_56(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(56, __VA_ARGS__)
#define Z_LISTIFY_58(F, sep, ...) \
    Z_LISTIFY_57(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(57, __VA_ARGS__)
#define Z_LISTIFY_59(F, sep, ...) \
    Z_LISTIFY_58(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(58, __VA_ARGS__)
#define Z_LISTIFY_60(F, sep, ...) \
    Z_LISTIFY_59(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(59, __VA_ARGS__)
#define Z_LISTIFY_61(F, sep, ...) \
    Z_LISTIFY_60(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(60, __VA_ARGS__)
#define Z_LISTIFY_62(F, sep, ...) \
    Z_LISTIFY_61(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(61, __VA_ARGS__)
#define Z_LISTIFY_63(F, sep, ...) \
    Z_LISTIFY_62(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(62, __VA_ARGS__)
#define Z_LISTIFY_64(F, sep, ...) \
    Z_LISTIFY_63(F, sep, __VA_ARGS__) __DEBRACKET sep \
    F(63, __VA_ARGS__)
// clang-format on

/* Strip parentheses from separator: __DEBRACKET (, ) => , */
#define __DEBRACKET(...) __VA_ARGS__

#endif /* LISTIFY_H */

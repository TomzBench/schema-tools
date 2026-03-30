from enum import StrEnum


class Primitive(StrEnum):
    UINT8 = "uint8_t"
    INT8 = "int8_t"
    UINT16 = "uint16_t"
    INT16 = "int16_t"
    UINT32 = "uint32_t"
    INT32 = "int32_t"
    UINT64 = "uint64_t"
    INT64 = "int64_t"
    FLOAT = "float"
    DOUBLE = "double"
    BOOL = "bool"
    CHAR = "char"

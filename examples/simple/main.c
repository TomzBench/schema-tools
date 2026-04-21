#include <stdio.h>
#include <string.h>

#include "sensor.h"

int main(void) {
    /* Decode a JSON literal into a struct. */
    const char *json =
        "{\"id\":7,\"celsius\":18.2,"
        "\"humidity_pct\":43,\"label\":\"inlet\"}";

    struct sensor_reading decoded;
    int32_t rc = jsmn_decode_sensor_reading(&decoded, json, strlen(json));
    if (rc < 0) {
        fprintf(stderr, "decode failed: %d\n", rc);
        return 1;
    }

    printf("decoded: id=%u celsius=%.1f humidity_pct=%u label=%s\n",
           decoded.id,
           (double)decoded.celsius,
           decoded.humidity_pct,
           decoded.label);

    /* Encode a struct back to JSON. */
    struct sensor_reading reading = {
        .id = 42,
        .celsius = 23.5f,
        .humidity_pct = 61,
        .label = "ambient",
    };

    uint8_t buf[128];
    int32_t n = jsmn_encode_sensor_reading(buf, sizeof(buf), &reading);
    if (n < 0) {
        fprintf(stderr, "encode failed: %d\n", n);
        return 1;
    }

    printf("encoded: %.*s\n", n, buf);
    return 0;
}

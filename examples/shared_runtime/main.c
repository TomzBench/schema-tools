#include <stdio.h>
#include <string.h>

#include "component-a.h"
#include "component-b.h"

int main(void) {
    /* Round-trip a sensor_reading via component-a. */
    const char *sensor_json =
        "{\"id\":7,\"celsius\":18.2,"
        "\"humidity_pct\":43,\"label\":\"inlet\"}";

    struct comp_a_sensor_reading sensor;
    int32_t rc = comp_a_decode_sensor_reading(
        &sensor, sensor_json, strlen(sensor_json));
    if (rc < 0) {
        fprintf(stderr, "sensor decode failed: %d\n", rc);
        return 1;
    }
    printf("sensor:    id=%u celsius=%.1f humidity_pct=%u label=%s\n",
           sensor.id,
           (double)sensor.celsius,
           sensor.humidity_pct,
           sensor.label);

    /* Round-trip a device_heartbeat via component-b. */
    const char *device_json =
        "{\"device_id\":42,\"uptime_s\":3600,\"online\":true}";

    struct comp_b_device_heartbeat device;
    rc = comp_b_decode_device_heartbeat(
        &device, device_json, strlen(device_json));
    if (rc < 0) {
        fprintf(stderr, "device decode failed: %d\n", rc);
        return 1;
    }
    printf("heartbeat: device_id=%u uptime_s=%u online=%s\n",
           device.device_id,
           device.uptime_s,
           device.online ? "true" : "false");

    return 0;
}

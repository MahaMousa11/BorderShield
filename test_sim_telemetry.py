import time
from mavlink_telemetry import MAVLinkTelemetry

print("=== BorderShield SITL Telemetry Test ===")

telemetry = MAVLinkTelemetry(
    connection_string="udpin:127.0.0.1:14552"
)

print("Starting telemetry...")
telemetry.start()

try:
    while True:
        data = telemetry.get_telemetry()
        print(data)
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping...")
    telemetry.stop()

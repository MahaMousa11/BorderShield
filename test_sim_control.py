import time
from mavlink_telemetry import MAVLinkTelemetry

print("=== BorderShield SITL Control Test ===")

telemetry = MAVLinkTelemetry(
    connection_string="udpin:127.0.0.1:14552"
)

telemetry.start()

print("Waiting for connection...")

while True:
    data = telemetry.get_telemetry()
    if data.get("connected"):
        break
    time.sleep(0.5)

print("Connected!")
print("Current mode:", telemetry.get_telemetry().get("flight_mode"))

print("Changing mode to GUIDED...")
telemetry.set_mode("GUIDED")

time.sleep(3)

print("New mode:", telemetry.get_telemetry().get("flight_mode"))

telemetry.stop()

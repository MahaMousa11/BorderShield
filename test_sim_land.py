import time
from mavlink_telemetry import MAVLinkTelemetry

print("=== BorderShield SITL Landing Test ===")

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
print("Current altitude:", telemetry.get_telemetry().get("altitude"))

print("Setting LAND mode...")
telemetry.set_mode("LAND")

while True:
    data = telemetry.get_telemetry()

    alt = data.get("altitude", 0)
    armed = data.get("armed")

    print(
        "Mode:", data.get("flight_mode"),
        "| Armed:", armed,
        "| Alt:", round(alt, 2)
    )

    if not armed:
        print("=== LANDING COMPLETE / DISARMED ===")
        break

    time.sleep(1)

telemetry.stop()

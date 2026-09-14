import time
from pymavlink import mavutil
from mavlink_telemetry import MAVLinkTelemetry

print("=== BorderShield SITL Takeoff Test ===")

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

print("Setting mode to GUIDED...")
telemetry.set_mode("GUIDED")
time.sleep(2)

print("Arming...")
telemetry.send_command_long(
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    param1=1
)

timeout = time.time() + 10

while time.time() < timeout:
    data = telemetry.get_telemetry()

    if data.get("armed"):
        print("ARMED")
        break

    time.sleep(0.5)
else:
    print("ARM FAILED")
    telemetry.stop()
    raise SystemExit

TARGET_ALT = 10

print("Taking off to 10 meters...")

telemetry.send_command_long(
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    param7=TARGET_ALT
)

while True:
    data = telemetry.get_telemetry()

    alt = data.get("altitude", 0)

    print(
        "Mode:", data.get("flight_mode"),
        "| Armed:", data.get("armed"),
        "| Alt:", round(alt, 2)
    )

    if alt >= 9:
        print("=== TAKEOFF SUCCESS ===")
        break

    time.sleep(1)

telemetry.stop()

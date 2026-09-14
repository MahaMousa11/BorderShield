import time
import math

from pymavlink import mavutil
from mavlink_telemetry import MAVLinkTelemetry


# ============================================================
# BORDER SHIELD - RECON PATROL SITL TEST
# ============================================================

CONNECTION = "udpin:0.0.0.0:14552"
TAKEOFF_ALT = 10.0

# How close the drone must be to consider waypoint reached
WAYPOINT_RADIUS_M = 2.5

# Max time allowed for each waypoint
WAYPOINT_TIMEOUT = 60


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def distance_m(lat1, lon1, lat2, lon2):
    """
    Calculate approximate distance between two GPS points in meters.
    """

    R = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2.0) ** 2
    )

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def offset_gps(lat, lon, north_m, east_m):
    """
    Create a GPS coordinate a given number of meters
    north/east from the original position.
    """

    earth_radius = 6378137.0

    new_lat = lat + math.degrees(north_m / earth_radius)

    new_lon = lon + math.degrees(
        east_m /
        (earth_radius * math.cos(math.radians(lat)))
    )

    return new_lat, new_lon


def goto_global(telemetry, lat, lon, alt):
    """
    Send Recon Drone to GPS coordinate in GUIDED mode.
    """

    if telemetry.mav is None:
        raise RuntimeError("MAVLink connection is not open")

    target_system = telemetry.mav.target_system
    target_component = telemetry.mav.target_component

    print(
        "\nGOTO ->",
        "LAT:", round(lat, 7),
        "LON:", round(lon, 7),
        "ALT:", alt
    )

    telemetry.mav.mav.set_position_target_global_int_send(
        0,
        target_system,
        target_component,

        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,

        # Position enabled
        # Velocity / acceleration / yaw ignored
        0b0000111111111000,

        int(lat * 1e7),
        int(lon * 1e7),
        float(alt),

        0, 0, 0,       # velocity
        0, 0, 0,       # acceleration
        0,             # yaw
        0              # yaw rate
    )


def wait_for_connection(telemetry):

    print("Waiting for Recon Drone connection...")

    while True:

        data = telemetry.get_telemetry()

        if data.get("connected"):
            print("Recon connected.")
            return data

        time.sleep(0.5)


def wait_until_armed(telemetry, timeout=15):

    end_time = time.time() + timeout

    while time.time() < end_time:

        data = telemetry.get_telemetry()

        if data.get("armed"):
            print("Recon ARMED.")
            return True

        time.sleep(0.5)

    return False


def wait_for_takeoff(telemetry, target_alt):

    print("Waiting for takeoff...")

    while True:

        data = telemetry.get_telemetry()

        alt = data.get("altitude", 0.0)

        print(
            "Mode:", data.get("flight_mode"),
            "| Armed:", data.get("armed"),
            "| Alt:", round(alt, 2)
        )

        if alt >= target_alt - 1.0:
            print("\n=== TAKEOFF SUCCESS ===")
            return

        time.sleep(1)


def wait_for_waypoint(telemetry, target_lat, target_lon):

    start_time = time.time()

    while True:

        data = telemetry.get_telemetry()

        current_lat = data.get("latitude", 0.0)
        current_lon = data.get("longitude", 0.0)
        altitude = data.get("altitude", 0.0)

        distance = distance_m(
            current_lat,
            current_lon,
            target_lat,
            target_lon
        )

        print(
            "Distance:", round(distance, 2), "m",
            "| Alt:", round(altitude, 2), "m"
        )

        if distance <= WAYPOINT_RADIUS_M:

            print("WAYPOINT REACHED.")
            return True

        if time.time() - start_time > WAYPOINT_TIMEOUT:

            print("WARNING: Waypoint timeout.")
            return False

        time.sleep(1)


def wait_for_landing(telemetry):

    print("\nLanding...")

    while True:

        data = telemetry.get_telemetry()

        altitude = data.get("altitude", 0.0)
        armed = data.get("armed")

        print(
            "Mode:", data.get("flight_mode"),
            "| Armed:", armed,
            "| Alt:", round(altitude, 2)
        )

        if not armed:

            print("\n=== LANDING COMPLETE / DISARMED ===")
            return

        time.sleep(1)


# ============================================================
# MAIN MISSION
# ============================================================

print("")
print("============================================")
print("   BORDER SHIELD - RECON PATROL SITL TEST")
print("============================================")
print("")


telemetry = MAVLinkTelemetry(
    connection_string=CONNECTION
)

telemetry.start()


try:

    # --------------------------------------------------------
    # 1. CONNECT
    # --------------------------------------------------------

    initial_data = wait_for_connection(telemetry)

    home_lat = initial_data.get("latitude")
    home_lon = initial_data.get("longitude")

    print("")
    print("HOME POSITION")
    print("LAT:", home_lat)
    print("LON:", home_lon)


    # --------------------------------------------------------
    # 2. CREATE PATROL ROUTE
    # --------------------------------------------------------

    # Small test patrol around the simulated base

    wp1 = offset_gps(
        home_lat,
        home_lon,
        north_m=20,
        east_m=0
    )

    wp2 = offset_gps(
        home_lat,
        home_lon,
        north_m=20,
        east_m=20
    )

    wp3 = offset_gps(
        home_lat,
        home_lon,
        north_m=0,
        east_m=20
    )


    patrol_points = [
        wp1,
        wp2,
        wp3
    ]


    print("")
    print("PATROL ROUTE CREATED")

    for i, point in enumerate(patrol_points, start=1):

        print(
            "WP" + str(i),
            "LAT:", round(point[0], 7),
            "LON:", round(point[1], 7)
        )


    # --------------------------------------------------------
    # 3. GUIDED MODE
    # --------------------------------------------------------

    print("")
    print("Setting GUIDED mode...")

    telemetry.set_mode("GUIDED")

    time.sleep(2)


    # --------------------------------------------------------
    # 4. ARM
    # --------------------------------------------------------

    print("Arming Recon Drone...")

    telemetry.send_command_long(
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        param1=1
    )


    if not wait_until_armed(telemetry):

        raise RuntimeError("ARM failed")


    # --------------------------------------------------------
    # 5. TAKEOFF
    # --------------------------------------------------------

    print("")
    print(
        "Taking off to",
        TAKEOFF_ALT,
        "meters..."
    )


    telemetry.send_command_long(
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        param7=TAKEOFF_ALT
    )


    wait_for_takeoff(
        telemetry,
        TAKEOFF_ALT
    )


    # --------------------------------------------------------
    # 6. PATROL
    # --------------------------------------------------------

    print("")
    print("======================")
    print("   PATROL STARTED")
    print("======================")


    for index, waypoint in enumerate(
        patrol_points,
        start=1
    ):

        print("")
        print(
            "Moving to Patrol Point",
            index
        )

        goto_global(
            telemetry,
            waypoint[0],
            waypoint[1],
            TAKEOFF_ALT
        )

        reached = wait_for_waypoint(
            telemetry,
            waypoint[0],
            waypoint[1]
        )

        if not reached:

            print(
                "Skipping to next waypoint."
            )


    # --------------------------------------------------------
    # 7. RETURN TO HOME POSITION
    # --------------------------------------------------------

    print("")
    print("======================")
    print("   RETURNING TO BASE")
    print("======================")


    goto_global(
        telemetry,
        home_lat,
        home_lon,
        TAKEOFF_ALT
    )


    wait_for_waypoint(
        telemetry,
        home_lat,
        home_lon
    )


    # --------------------------------------------------------
    # 8. LAND
    # --------------------------------------------------------

    print("")
    print("Setting LAND mode...")

    telemetry.set_mode("LAND")


    wait_for_landing(
        telemetry
    )


    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print("")
    print("============================================")
    print("     RECON PATROL MISSION SUCCESS")
    print("============================================")


except KeyboardInterrupt:

    print("")
    print("Mission interrupted by operator.")


except Exception as error:

    print("")
    print("MISSION ERROR:")
    print(error)


finally:

    telemetry.stop()

    print("Telemetry stopped.")

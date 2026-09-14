from pathlib import Path

OUT = Path.home() / "Desktop" / "project" / "bordershield_world.sdf"


# ============================================================
# HELPERS
# ============================================================

def material(r, g, b):
    return f"""
          <material>
            <ambient>{r} {g} {b} 1</ambient>
            <diffuse>{r} {g} {b} 1</diffuse>
            <specular>0.04 0.04 0.04 1</specular>
          </material>
"""


def box_visual(name, x, y, z, sx, sy, sz, r, g, b, yaw=0):
    return f"""
        <visual name="{name}">
          <pose>{x} {y} {z} 0 0 {yaw}</pose>

          <geometry>
            <box>
              <size>{sx} {sy} {sz}</size>
            </box>
          </geometry>

          {material(r, g, b)}
        </visual>
"""


def cylinder_visual(name, x, y, z, radius, length, r, g, b):
    return f"""
        <visual name="{name}">
          <pose>{x} {y} {z} 0 0 0</pose>

          <geometry>
            <cylinder>
              <radius>{radius}</radius>
              <length>{length}</length>
            </cylinder>
          </geometry>

          {material(r, g, b)}
        </visual>
"""


def sphere_visual(name, x, y, z, radius, r, g, b):
    return f"""
        <visual name="{name}">
          <pose>{x} {y} {z} 0 0 0</pose>

          <geometry>
            <sphere>
              <radius>{radius}</radius>
            </sphere>
          </geometry>

          {material(r, g, b)}
        </visual>
"""


def static_model(name, visuals):
    return f"""
    <model name="{name}">
      <static>true</static>

      <link name="link">
        {visuals}
      </link>
    </model>
"""


# ============================================================
# ROAD MARKINGS
# ============================================================

road_markings = ""

for i, x in enumerate(range(7, 48, 7), 1):
    road_markings += box_visual(
        f"center_dash_{i}",
        x, 0, 0.085,
        3.5, 0.16, 0.025,
        0.93, 0.93, 0.88
    )


# ============================================================
# OPERATIONS BUILDING
# ============================================================

operations = ""

operations += box_visual(
    "main_building",
    5.5, -7.5, 1.65,
    7.0, 4.5, 3.3,
    0.43, 0.38, 0.30
)

operations += box_visual(
    "flat_roof",
    5.5, -7.5, 3.4,
    7.5, 5.0, 0.18,
    0.22, 0.21, 0.18
)

operations += box_visual(
    "front_door",
    5.5, -5.22, 1.0,
    1.2, 0.05, 2.0,
    0.13, 0.12, 0.10
)

operations += box_visual(
    "front_window_left",
    3.4, -5.20, 1.8,
    1.25, 0.05, 0.75,
    0.07, 0.23, 0.31
)

operations += box_visual(
    "front_window_right",
    7.6, -5.20, 1.8,
    1.25, 0.05, 0.75,
    0.07, 0.23, 0.31
)


# ============================================================
# WATCHTOWER LEFT
# ============================================================

tower_left = ""

tower_left += box_visual(
    "column",
    43, 19, 3.0,
    1.2, 1.2, 6.0,
    0.38, 0.34, 0.27
)

tower_left += box_visual(
    "room",
    43, 19, 6.5,
    3.0, 3.0, 1.6,
    0.29, 0.28, 0.24
)

tower_left += box_visual(
    "window",
    43, 17.47, 6.55,
    2.2, 0.05, 0.60,
    0.05, 0.18, 0.24
)

tower_left += box_visual(
    "roof",
    43, 19, 7.45,
    3.4, 3.4, 0.18,
    0.17, 0.17, 0.16
)


# ============================================================
# WATCHTOWER RIGHT
# ============================================================

tower_right = ""

tower_right += box_visual(
    "column",
    43, -19, 3.0,
    1.2, 1.2, 6.0,
    0.38, 0.34, 0.27
)

tower_right += box_visual(
    "room",
    43, -19, 6.5,
    3.0, 3.0, 1.6,
    0.29, 0.28, 0.24
)

tower_right += box_visual(
    "window",
    43, -17.47, 6.55,
    2.2, 0.05, 0.60,
    0.05, 0.18, 0.24
)

tower_right += box_visual(
    "roof",
    43, -19, 7.45,
    3.4, 3.4, 0.18,
    0.17, 0.17, 0.16
)


# ============================================================
# PERSON TARGET
# NOW BEHIND THE BORDER WALL
# ============================================================

person = ""

person += cylinder_visual(
    "torso",
    52, 12, 1.15,
    0.22, 0.90,
    0.12, 0.14, 0.55
)

person += sphere_visual(
    "head",
    52, 12, 1.82,
    0.20,
    0.76, 0.57, 0.42
)

person += cylinder_visual(
    "left_leg",
    51.88, 12, 0.45,
    0.075, 0.80,
    0.07, 0.07, 0.07
)

person += cylinder_visual(
    "right_leg",
    52.12, 12, 0.45,
    0.075, 0.80,
    0.07, 0.07, 0.07
)


# ============================================================
# VEHICLE TARGET
# NOW BEHIND THE BORDER WALL
# ============================================================

vehicle = ""

vehicle += box_visual(
    "body",
    55, -12, 0.65,
    4.2, 1.9, 0.75,
    0.48, 0.07, 0.05,
    yaw=0.20
)

vehicle += box_visual(
    "cabin",
    54.7, -12, 1.25,
    2.0, 1.50, 0.68,
    0.14, 0.18, 0.20,
    yaw=0.20
)


# ============================================================
# FINAL WORLD
# ============================================================

world = f"""<?xml version="1.0"?>
<sdf version="1.9">

  <world name="bordershield_world">

    <physics name="1ms" type="ignore">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin filename="gz-sim-physics-system"
            name="gz::sim::systems::Physics"/>

    <plugin filename="gz-sim-sensors-system"
            name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>

    <plugin filename="gz-sim-user-commands-system"
            name="gz::sim::systems::UserCommands"/>

    <plugin filename="gz-sim-scene-broadcaster-system"
            name="gz::sim::systems::SceneBroadcaster"/>

    <plugin filename="gz-sim-imu-system"
            name="gz::sim::systems::Imu"/>

    <plugin filename="gz-sim-navsat-system"
            name="gz::sim::systems::NavSat"/>


    <!-- CAMERA -->

    <gui fullscreen="0">

      <camera name="user_camera">
        <pose>-25 -28 24 0 0.43 0.78</pose>
        <view_controller>orbit</view_controller>
      </camera>

    </gui>


    <!-- ENVIRONMENT -->

    <scene>
      <ambient>0.72 0.68 0.60</ambient>
      <background>0.48 0.67 0.85</background>
      <sky/>
      <shadows>true</shadows>
    </scene>


    <light type="directional" name="sun">

      <cast_shadows>true</cast_shadows>

      <pose>0 0 80 0 0 0</pose>

      <diffuse>1.0 0.93 0.78 1</diffuse>
      <specular>0.35 0.34 0.30 1</specular>

      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>

      <direction>-0.45 0.15 -0.9</direction>

    </light>


    <!-- GPS ORIGIN -->

    <spherical_coordinates>

      <latitude_deg>-35.363262</latitude_deg>
      <longitude_deg>149.165237</longitude_deg>

      <elevation>584</elevation>

      <heading_deg>0</heading_deg>

      <surface_model>EARTH_WGS84</surface_model>

    </spherical_coordinates>


    <!-- NAVSAT -->

    <model name="axes">

      <static>true</static>

      <link name="link">

        <sensor name="navsat_sensor" type="navsat">

          <always_on>true</always_on>

          <update_rate>1</update_rate>

        </sensor>

      </link>

    </model>


    <!-- DESERT GROUND -->

    <model name="desert_ground">

      <static>true</static>

      <link name="ground">

        <collision name="ground_collision">

          <geometry>
            <box>
              <size>150 80 0.30</size>
            </box>
          </geometry>

        </collision>

        <visual name="ground_visual">

          <pose>30 0 -0.16 0 0 0</pose>

          <geometry>
            <box>
              <size>150 80 0.30</size>
            </box>
          </geometry>

          {material(0.64, 0.51, 0.32)}

        </visual>

      </link>

    </model>


    <!-- BASE -->

    <model name="bordershield_base">

      <static>true</static>

      <link name="base">

        {box_visual(
            "base_surface",
            0, 0, 0.04,
            21, 16, 0.10,
            0.32, 0.32, 0.30
        )}

      </link>

    </model>


    <!-- MAIN ROAD -->

    <model name="main_road">

      <static>true</static>

      <link name="road">

        {box_visual(
            "road_surface",
            28, 0, 0.035,
            56, 7.5, 0.07,
            0.13, 0.13, 0.12
        )}

        {road_markings}

        {box_visual(
            "left_edge",
            28, 3.85, 0.075,
            56, 0.12, 0.03,
            0.88, 0.72, 0.07
        )}

        {box_visual(
            "right_edge",
            28, -3.85, 0.075,
            56, 0.12, 0.03,
            0.88, 0.72, 0.07
        )}

      </link>

    </model>


    <!-- RECON PAD -->

    <model name="recon_pad">

      <static>true</static>

      <link name="pad">

        {cylinder_visual(
            "pad_surface",
            -3.0, 2.2, 0.11,
            1.65, 0.07,
            0.24, 0.34, 0.25
        )}

        {box_visual(
            "H_horizontal",
            -3.0, 2.2, 0.17,
            1.25, 0.16, 0.03,
            0.92, 0.92, 0.86
        )}

        {box_visual(
            "H_vertical",
            -3.0, 2.2, 0.17,
            0.16, 1.10, 0.03,
            0.92, 0.92, 0.86
        )}

      </link>

    </model>


    <!-- RESPONSE PAD -->

    <model name="response_pad">

      <static>true</static>

      <link name="pad">

        {cylinder_visual(
            "pad_surface",
            3.0, 2.2, 0.11,
            1.65, 0.07,
            0.38, 0.24, 0.22
        )}

        {box_visual(
            "H_horizontal",
            3.0, 2.2, 0.17,
            1.25, 0.16, 0.03,
            0.92, 0.92, 0.86
        )}

        {box_visual(
            "H_vertical",
            3.0, 2.2, 0.17,
            0.16, 1.10, 0.03,
            0.92, 0.92, 0.86
        )}

      </link>

    </model>


    <!-- RECON DRONE -->

    <include>

      <uri>model://iris_with_gimbal_recon</uri>

      <name>recon_drone</name>

      <pose degrees="true">
        -3.0 2.2 0.25 0 0 90
      </pose>

    </include>


    <!-- RESPONSE DRONE -->

    <include>

      <uri>model://iris_with_gimbal_response</uri>

      <name>response_drone</name>

      <pose degrees="true">
        3.0 2.2 0.25 0 0 90
      </pose>

    </include>


    <!-- OPERATIONS BUILDING -->

    {static_model(
        "operations_building",
        operations
    )}


    <!-- BORDER WALL LEFT -->

    <model name="border_wall_left">

      <static>true</static>

      <link name="wall">

        {box_visual(
            "wall",
            43, 19, 1.25,
            0.35, 30, 2.5,
            0.43, 0.37, 0.28
        )}

      </link>

    </model>


    <!-- BORDER WALL RIGHT -->

    <model name="border_wall_right">

      <static>true</static>

      <link name="wall">

        {box_visual(
            "wall",
            43, -19, 1.25,
            0.35, 30, 2.5,
            0.43, 0.37, 0.28
        )}

      </link>

    </model>


    <!-- BORDER GATE -->

    <model name="border_gate">

      <static>true</static>

      <link name="gate">

        {cylinder_visual(
            "left_gate_post",
            43, 4.2, 1.7,
            0.13, 3.4,
            0.25, 0.23, 0.19
        )}

        {cylinder_visual(
            "right_gate_post",
            43, -4.2, 1.7,
            0.13, 3.4,
            0.25, 0.23, 0.19
        )}

        {box_visual(
            "gate_top",
            43, 0, 3.25,
            0.22, 8.6, 0.20,
            0.35, 0.30, 0.23
        )}

      </link>

    </model>


    <!-- WATCHTOWERS -->

    {static_model(
        "watchtower_left",
        tower_left
    )}

    {static_model(
        "watchtower_right",
        tower_right
    )}


    <!-- ================================================= -->
    <!-- TARGETS BEHIND THE BORDER                          -->
    <!-- ================================================= -->

    {static_model(
        "person_target",
        person
    )}

    {static_model(
        "vehicle_target",
        vehicle
    )}


    <!-- DETECTION LINE -->

    <model name="border_marker">

      <static>true</static>

      <link name="marker">

        {box_visual(
            "marker",
            49, 0, 0.06,
            0.18, 34, 0.07,
            0.86, 0.64, 0.06
        )}

      </link>

    </model>


  </world>

</sdf>
"""


OUT.write_text(world)

print("")
print("==============================================")
print(" BorderShield CLEAN World V3.1 generated")
print("==============================================")
print("")
print("Target placement:")
print("  Border wall X = 43")
print("  Person target X = 52")
print("  Vehicle target X = 55")
print("")
print("Both targets are now BEHIND the border.")
print("")
print("Saved to:")
print(OUT)
print("")

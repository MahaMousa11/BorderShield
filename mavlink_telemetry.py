import threading
import time
import math
import re
import copy
import pymavlink
from pymavlink import mavutil

# ----------------------------------------------------
# 1. MONKEY-PATCH PYMAVLINK TO PREVENT NoneType CRASH
# ----------------------------------------------------
_orig_add_message = pymavlink.mavutil.add_message

def patched_add_message(messages, mtype, msg):
    if messages is None:
        return
    if msg._instance_field is None or getattr(msg, msg._instance_field, None) is None:
        messages[mtype] = msg
        return
    instance_value = getattr(msg, msg._instance_field)
    if not mtype in messages:
        messages[mtype] = copy.copy(msg)
        messages[mtype]._instances = {}
        messages[mtype]._instances[instance_value] = msg
        messages["%s[%s]" % (mtype, str(instance_value))] = copy.copy(msg)
        return
    
    # Defensive fix for TypeError: 'NoneType' object does not support item assignment
    if not hasattr(messages[mtype], '_instances') or messages[mtype]._instances is None:
        messages[mtype]._instances = {}
        
    messages[mtype]._instances[instance_value] = msg
    prev_instances = messages[mtype]._instances
    messages[mtype] = copy.copy(msg)
    messages[mtype]._instances = prev_instances
    messages["%s[%s]" % (mtype, str(instance_value))] = copy.copy(msg)

pymavlink.mavutil.add_message = patched_add_message


DEFAULT_CONNECTION = '/dev/ttyACM0'
DEFAULT_BAUD = 115200

# ArduPilot Copter Flight Modes mapping
ARDUPILOT_COPTER_MODES = {
    0: "STABILIZE",
    1: "ACRO",
    2: "ALT_HOLD",
    3: "AUTO",
    4: "GUIDED",
    5: "LOITER",
    6: "RTL",
    7: "CIRCLE",
    9: "LAND",
    11: "DRIFT",
    13: "SPORT",
    14: "FLIP",
    15: "AUTOTUNE",
    16: "POSHOLD",
    17: "BRAKE",
    18: "THROW",
    19: "AVOID_ADSB",
    20: "GUIDED_NOGPS",
    21: "SMART_RTL",
    22: "FLOWHOLD",
    23: "FOLLOW",
    24: "ZIGZAG"
}

def initialize_target_from_heartbeat(mav, heartbeat, prefix="MAVLinkTelemetry"):
    source_system = heartbeat.get_srcSystem()
    source_component = heartbeat.get_srcComponent()
    print(prefix + ": HEARTBEAT source system/component: " + str(source_system) + "/" + str(source_component))
    print(prefix + ": Connection target before init: " + str(mav.target_system) + "/" + str(mav.target_component))

    if source_system:
        mav.target_system = source_system
    if source_component:
        mav.target_component = source_component

    print(prefix + ": Connection target after init: " + str(mav.target_system) + "/" + str(mav.target_component))

def request_data_streams(mav, rate_hz=4, prefix="MAVLinkTelemetry"):
    mav.mav.request_data_stream_send(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        rate_hz,
        1
    )
    print(prefix + ": Requested data streams at " + str(rate_hz) + "Hz.")

# ----------------------------------------------------
# HEARTBEAT FILTERING HELPERS
# ----------------------------------------------------
def is_real_autopilot_heartbeat(msg):
    if msg.get_type() != 'HEARTBEAT':
        return False
    sys_id = msg.get_srcSystem()
    comp_id = msg.get_srcComponent()
    
    # Flight controller is system ID 1, component ID 1
    if sys_id == 0 or comp_id != 1:
        return False
        
    # Exclude companion computer components and GCS component types
    # MAV_TYPE_ONBOARD_CONTROLLER = 18, MAV_TYPE_GCS = 6
    if msg.type in [mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER, mavutil.mavlink.MAV_TYPE_GCS]:
        return False
        
    # Autopilot type must be ArduPilot
    # MAV_AUTOPILOT_ARDUPILOTMEGA = 3
    if msg.autopilot != mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA:
        return False
        
    return True

def wait_for_autopilot_heartbeat(mav, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = mav.recv_match(type='HEARTBEAT', blocking=True, timeout=1.0)
        if msg is not None and is_real_autopilot_heartbeat(msg):
            return msg
    return None


import glob

def detect_orange_cube_device(baud=115200):
    # 1. Search candidates
    by_id_paths = glob.glob("/dev/serial/by-id/*")
    tty_acm_paths = glob.glob("/dev/ttyACM*")
    tty_usb_paths = glob.glob("/dev/ttyUSB*")
    
    # 2. Prefer stable by-id paths containing cubepilot or cubeorange
    preferred_by_id = []
    other_by_id = []
    for path in by_id_paths:
        name = path.lower()
        if "cubepilot" in name or "cubeorange" in name:
            preferred_by_id.append(path)
        else:
            other_by_id.append(path)
            
    candidates = preferred_by_id + other_by_id + tty_acm_paths + tty_usb_paths
    # Deduplicate candidates preserving order
    seen = set()
    deduped_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped_candidates.append(c)
            
    print("MAVLink candidates: " + str(deduped_candidates))
    
    # 3. Probe candidates one at a time
    for path in deduped_candidates:
        print("Probing: " + path)
        mav = None
        try:
            mav = mavutil.mavlink_connection(path, baud=baud)
            # Wait up to 3 seconds for a heartbeat
            msg = mav.wait_heartbeat(timeout=3.0)
            if msg is None:
                print("Rejected: timeout waiting for heartbeat")
                mav.close()
                continue
                
            # 4. Validate Orange Cube autopilot heartbeat
            sys_id = msg.get_srcSystem()
            comp_id = msg.get_srcComponent()
            
            # System ID 1, Component ID 1
            if sys_id != 1 or comp_id != 1:
                print("Rejected: heartbeat source system/component was " + str(sys_id) + "/" + str(comp_id) + " (expected 1/1)")
                mav.close()
                continue
                
            # Autopilot type must be ArduPilot
            if msg.autopilot != mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA:
                print("Rejected: autopilot type was " + str(msg.autopilot) + " (expected 3)")
                mav.close()
                continue
                
            # Reject GCS or onboard controller types
            if msg.type in [mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER, mavutil.mavlink.MAV_TYPE_GCS]:
                print("Rejected: vehicle type was " + str(msg.type))
                mav.close()
                continue
                
            print("SELECTED ORANGE CUBE DEVICE: " + path)
            mav.close()
            return path
            
        except Exception as e:
            print("Rejected: error opening or reading: " + str(e))
            if mav is not None:
                try:
                    mav.close()
                except Exception:
                    pass
                    
    print("SELECTED ORANGE CUBE DEVICE: None")
    return None


class MAVLinkTelemetry:
    def __init__(self, connection_string=DEFAULT_CONNECTION, baud=DEFAULT_BAUD,
                 source_system=1, source_component=191, dialect="ardupilotmega"):
        self.baud = baud
        self.source_system = source_system
        self.source_component = source_component
        self.dialect = dialect
        self.connected = False
        
        # Shared MAVLink connection references
        self.mav = None
        self.master = None
        
        # Automatic Orange Cube USB device detection if default or None is passed
        if connection_string is None or connection_string == DEFAULT_CONNECTION:
            detected = detect_orange_cube_device(baud=baud)
            if detected:
                self.connection_string = detected
            else:
                self.connection_string = DEFAULT_CONNECTION
        else:
            self.connection_string = connection_string
        
        # Shared state structures initialized exactly once and never set to None
        self.telemetry_state = {
            "connected": False,
            "ground_speed": 0.0,
            "timestamp": 0.0
        }
        self.gps_state = {
            "gps_fix": 0,
            "satellites": 0
        }
        self.position_state = {
            "latitude": 0.0,
            "longitude": 0.0,
            "altitude": 0.0
        }
        self.attitude_state = {
            "heading": 0.0,
            "pitch": 0.0,
            "roll": 0.0
        }
        self.heartbeat_state = {
            "armed": False,
            "flight_mode": "UNKNOWN",
            "last_heartbeat_time": 0.0
        }
        self.message_cache = {}
        
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._diagnostic_seen = set()

    # Properties to maintain backward compatibility with direct property access
    @property
    def latitude(self):
        return self.position_state["latitude"]
    @latitude.setter
    def latitude(self, val):
        self.position_state["latitude"] = val

    @property
    def longitude(self):
        return self.position_state["longitude"]
    @longitude.setter
    def longitude(self, val):
        self.position_state["longitude"] = val

    @property
    def altitude(self):
        return self.position_state["altitude"]
    @altitude.setter
    def altitude(self, val):
        self.position_state["altitude"] = val

    @property
    def heading(self):
        return self.attitude_state["heading"]
    @heading.setter
    def heading(self, val):
        self.attitude_state["heading"] = val

    @property
    def pitch(self):
        return self.attitude_state["pitch"]
    @pitch.setter
    def pitch(self, val):
        self.attitude_state["pitch"] = val

    @property
    def roll(self):
        return self.attitude_state["roll"]
    @roll.setter
    def roll(self, val):
        self.attitude_state["roll"] = val

    @property
    def ground_speed(self):
        return self.telemetry_state["ground_speed"]
    @ground_speed.setter
    def ground_speed(self, val):
        self.telemetry_state["ground_speed"] = val

    @property
    def gps_fix(self):
        return self.gps_state["gps_fix"]
    @gps_fix.setter
    def gps_fix(self, val):
        self.gps_state["gps_fix"] = val

    @property
    def satellites(self):
        return self.gps_state["satellites"]
    @satellites.setter
    def satellites(self, val):
        self.gps_state["satellites"] = val

    @property
    def flight_mode(self):
        return self.heartbeat_state["flight_mode"]
    @flight_mode.setter
    def flight_mode(self, val):
        self.heartbeat_state["flight_mode"] = val

    @property
    def armed(self):
        return self.heartbeat_state["armed"]
    @armed.setter
    def armed(self, val):
        self.heartbeat_state["armed"] = val

    @property
    def timestamp(self):
        return self.telemetry_state["timestamp"]
    @timestamp.setter
    def timestamp(self, val):
        self.telemetry_state["timestamp"] = val

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        print("MAVLinkTelemetry: Starting listener thread...")
        while not self._stop_event.is_set():
            try:
                print("MAVLinkTelemetry: Connecting to " + self.connection_string + " at " + str(self.baud) + " baud...")
                mav = mavutil.mavlink_connection(
                    self.connection_string,
                    baud=self.baud,
                    source_system=self.source_system,
                    source_component=self.source_component,
                    dialect=self.dialect
                )

                print("MAVLinkTelemetry: Waiting for HEARTBEAT from ArduPilot flight controller...")
                heartbeat = wait_for_autopilot_heartbeat(mav, timeout=15.0)
                if heartbeat is None:
                    raise RuntimeError("Timeout waiting for autopilot HEARTBEAT")

                initialize_target_from_heartbeat(mav, heartbeat)
                request_data_streams(mav, rate_hz=4)

                with self._lock:
                    self.mav = mav
                    self.master = mav
                    self._store_heartbeat(mav, heartbeat)
                
                while not self._stop_event.is_set():
                    # Receive any message
                    msg = mav.recv_match(blocking=True, timeout=1.0)
                    if msg is None:
                        # Timeout on recv_match
                        with self._lock:
                            if self.connected and (time.time() - self.telemetry_state["timestamp"] > 15.0):
                                print("MAVLinkTelemetry: Connection timeout (no heartbeats).")
                                self.connected = False
                                self.telemetry_state["connected"] = False
                                # Reset GPS validity safely if communication is lost
                                self.gps_state["gps_fix"] = 0
                                self.gps_state["satellites"] = 0
                        continue
                    
                    msg_type = msg.get_type()
                    self._forward_to_gcs(msg)

                    # Any valid MAVLink message proves that the link is alive.
                    # This prevents false disconnects in SITL when HEARTBEAT
                    # timing is sparse but telemetry is still flowing.
                    with self._lock:
                        self.connected = True
                        self.telemetry_state["connected"] = True
                        self.telemetry_state["timestamp"] = time.time()

                        # Cache the message
                        self.message_cache[msg_type] = msg
                    
                    if msg_type == 'HEARTBEAT':
                        if is_real_autopilot_heartbeat(msg):
                            with self._lock:
                                if not self.connected:
                                    try:
                                        initialize_target_from_heartbeat(mav, msg)
                                        request_data_streams(mav, rate_hz=4)
                                    except Exception as e:
                                        print("MAVLinkTelemetry: Error requesting streams: " + str(e))
                                
                                self._store_heartbeat(mav, msg)
                                
                    elif msg_type == 'GLOBAL_POSITION_INT':
                        with self._lock:
                            self.position_state["latitude"] = msg.lat / 1e7
                            self.position_state["longitude"] = msg.lon / 1e7
                            self.position_state["altitude"] = msg.relative_alt / 1000.0  # AGL altitude in meters
                            self.telemetry_state["timestamp"] = time.time()
                            self._print_once("GLOBAL_POSITION_INT",
                                             "MAVLinkTelemetry: Received GLOBAL_POSITION_INT lat=" + str(self.position_state["latitude"]) +
                                             " lon=" + str(self.position_state["longitude"]) +
                                             " rel_alt_m=" + str(self.position_state["altitude"]))
                            
                    elif msg_type == 'ATTITUDE':
                        with self._lock:
                            self.attitude_state["roll"] = math.degrees(msg.roll)
                            self.attitude_state["pitch"] = math.degrees(msg.pitch)
                            self.attitude_state["heading"] = math.degrees(msg.yaw) % 360.0
                            self.telemetry_state["timestamp"] = time.time()
                            self._print_once("ATTITUDE",
                                             "MAVLinkTelemetry: Received ATTITUDE roll=" + str(self.attitude_state["roll"]) +
                                             " pitch=" + str(self.attitude_state["pitch"]) +
                                             " heading=" + str(self.attitude_state["heading"]))
                            
                    elif msg_type == 'GPS_RAW_INT':
                        with self._lock:
                            self.gps_state["gps_fix"] = msg.fix_type
                            self.gps_state["satellites"] = msg.satellites_visible
                            self.telemetry_state["timestamp"] = time.time()
                            self._print_once("GPS_RAW_INT",
                                             "MAVLinkTelemetry: Received GPS_RAW_INT fix_type=" + str(self.gps_state["gps_fix"]) +
                                             " satellites=" + str(self.gps_state["satellites"]))
                            
                    elif msg_type == 'VFR_HUD':
                        with self._lock:
                            self.telemetry_state["ground_speed"] = msg.groundspeed
                            self.telemetry_state["timestamp"] = time.time()
                            
            except Exception as e:
                print("MAVLinkTelemetry: Error in listener: " + str(e))
                import traceback
                traceback.print_exc()
                with self._lock:
                    self.connected = False
                    self.telemetry_state["connected"] = False
                    # Make reconnect safe:
                    # - Reset GPS validity safely if communication is lost
                    self.gps_state["gps_fix"] = 0
                    self.gps_state["satellites"] = 0
                    
                    self.mav = None
                    self.master = None
                time.sleep(2)

    def _store_heartbeat(self, mav, msg):
        self.connected = True
        self.telemetry_state["connected"] = True
        self.heartbeat_state["last_heartbeat_time"] = time.time()
        self.telemetry_state["timestamp"] = time.time()
        self.heartbeat_state["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        self.heartbeat_state["flight_mode"] = ARDUPILOT_COPTER_MODES.get(msg.custom_mode, "UNKNOWN")
        if self.heartbeat_state["flight_mode"] == "UNKNOWN" and hasattr(mav, 'flightmode'):
            fm = mav.flightmode
            if fm and not str(fm).startswith("Mode("):
                self.heartbeat_state["flight_mode"] = str(fm)

    def _print_once(self, key, message):
        if key not in self._diagnostic_seen:
            print(message)
            self._diagnostic_seen.add(key)

    def get_data(self):
        with self._lock:
            # Check dynamically if connection is active
            active = self.connected and (time.time() - self.telemetry_state["timestamp"] < 15.0)
            
            # Return deepcopy to ensure caller cannot mutate state
            return copy.deepcopy({
                "connected": active,
                "latitude": self.position_state["latitude"],
                "longitude": self.position_state["longitude"],
                "altitude": self.position_state["altitude"],
                "heading": self.attitude_state["heading"],
                "pitch": self.attitude_state["pitch"],
                "roll": self.attitude_state["roll"],
                "ground_speed": self.telemetry_state["ground_speed"],
                "gps_fix": self.gps_state["gps_fix"],
                "satellites": self.gps_state["satellites"],
                "flight_mode": self.heartbeat_state["flight_mode"],
                "armed": self.heartbeat_state["armed"],
                "timestamp": self.telemetry_state["timestamp"]
            })

    def get_telemetry(self):
        return self.get_data()

    # ----------------------------------------------------
    # THREAD-SAFE TRANSMISSION METHODS
    # ----------------------------------------------------
    def _forward_to_gcs(self, msg):
        if not hasattr(self, "_gcs_udp_sock"):
            import socket
            self._gcs_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._gcs_udp_targets = ["169.254.7.55", "172.31.176.1"]
            
        try:
            buf = msg.get_msgbuf()
            for target in self._gcs_udp_targets:
                try:
                    self._gcs_udp_sock.sendto(buf, (target, 14560))
                except Exception:
                    pass
        except Exception:
            pass

    def _time_boot_ms(self):
        if not hasattr(self, "_start_monotonic"):
            self._start_monotonic = time.monotonic()
        return int((time.monotonic() - self._start_monotonic) * 1000) & 0xFFFFFFFF

    def _flush(self):
        try:
            if self.mav and hasattr(self.mav, "port") and self.mav.port:
                self.mav.port.flush()
        except Exception:
            pass

    def send_heartbeat(self):
        with self._write_lock:
            if self.mav is None:
                raise RuntimeError("MAVLink connection is not open")
            msg = self.mav.mav.heartbeat_encode(
                mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                mavutil.mavlink.MAV_STATE_ACTIVE,
            )
            self.mav.mav.send(msg)
            self._forward_to_gcs(msg)
            self._flush()

    def send_statustext(self, text, severity=mavutil.mavlink.MAV_SEVERITY_WARNING):
        if isinstance(text, str):
            text = text.encode("ascii", errors="replace")
        with self._write_lock:
            if self.mav is None:
                raise RuntimeError("MAVLink connection is not open")
            msg = self.mav.mav.statustext_encode(severity, text)
            self.mav.mav.send(msg)
            self._forward_to_gcs(msg)
            self._flush()

    def send_named_value_int(self, name, value, time_boot_ms=None):
        if isinstance(name, str):
            name = name.encode("ascii", errors="replace")
        if time_boot_ms is None:
            time_boot_ms = self._time_boot_ms()
        with self._write_lock:
            if self.mav is None:
                raise RuntimeError("MAVLink connection is not open")
            msg = self.mav.mav.named_value_int_encode(time_boot_ms, name, int(value))
            self.mav.mav.send(msg)
            self._forward_to_gcs(msg)
            self._flush()

    def send_named_value_float(self, name, value, time_boot_ms=None):
        if isinstance(name, str):
            name = name.encode("ascii", errors="replace")
        if time_boot_ms is None:
            time_boot_ms = self._time_boot_ms()
        with self._write_lock:
            if self.mav is None:
                raise RuntimeError("MAVLink connection is not open")
            msg = self.mav.mav.named_value_float_encode(time_boot_ms, name, float(value))
            self.mav.mav.send(msg)
            self._forward_to_gcs(msg)
            self._flush()

    def send_bs_alert(self, lat, lon, alt_m, confidence, target_class):
        lat = _validate_coordinate("lat", lat, -90.0, 90.0)
        lon = _validate_coordinate("lon", lon, -180.0, 180.0)
        alt_m = float(alt_m)
        confidence_float = _normalize_confidence(confidence)
        confidence_percent = int(round(confidence_float * 100.0))
        target_class = _clean_target_class(target_class)

        # Base text payload
        text = "BS,{:.7f},{:.7f},{:d},{}".format(
            lat,
            lon,
            confidence_percent,
            target_class,
        )
        if len(text) > 50:
            text = text[:50]

        time_boot_ms = self._time_boot_ms()

        print("MAVLinkTelemetry: sending STATUSTEXT " + text)
        self.send_statustext(text, severity=mavutil.mavlink.MAV_SEVERITY_WARNING)
        self.send_named_value_int(b"TGT_LAT", int(round(lat * 1e7)), time_boot_ms)
        self.send_named_value_int(b"TGT_LON", int(round(lon * 1e7)), time_boot_ms)
        self.send_named_value_float(b"TGT_CONF", float(confidence_float), time_boot_ms)

        print(
            "MAVLinkTelemetry: alert sent lat="
            + str(lat)
            + " lon="
            + str(lon)
            + " alt_m="
            + str(alt_m)
            + " confidence="
            + str(confidence_float)
            + " class="
            + target_class
        )
        return {
            "statustext": text,
            "target_lat_int": int(round(lat * 1e7)),
            "target_lon_int": int(round(lon * 1e7)),
            "target_confidence": confidence_float,
            "target_class": target_class,
        }

    def send_command_long(self, command, param1=0.0, param2=0.0, param3=0.0, param4=0.0, param5=0.0, param6=0.0, param7=0.0, target_system=None, target_component=None, confirmation=0):
        with self._write_lock:
            if self.mav is None:
                raise RuntimeError("MAVLink connection is not open")
            sys_id = target_system if target_system is not None else self.mav.target_system
            comp_id = target_component if target_component is not None else self.mav.target_component
            self.mav.mav.command_long_send(
                sys_id,
                comp_id,
                command,
                confirmation,
                param1, param2, param3, param4, param5, param6, param7
            )
            self._flush()

    def clear_command_ack(self):
        with self._lock:
            self.message_cache.pop("COMMAND_ACK", None)

    def wait_command_ack(self, command, timeout=15.0):
        end_time = time.time() + timeout

        while time.time() < end_time:
            with self._lock:
                msg = self.message_cache.get("COMMAND_ACK")

                if msg is not None and int(msg.command) == int(command):
                    return copy.deepcopy(msg)

            time.sleep(0.1)

        return None

    def set_mode(self, mode_name):
        mode_name = str(mode_name).upper()
        with self._write_lock:
            if self.mav is None:
                raise RuntimeError("MAVLink connection is not open")
            mapping = self.mav.mode_mapping()
            if not mapping or mode_name not in mapping:
                raise RuntimeError("Mode " + mode_name + " not available in ArduPilot mode mapping")
            mode_id = mapping[mode_name]
            target_system = getattr(self.mav, "target_system", 0)
            if not target_system:
                raise RuntimeError("MAVLink target_system is not initialized")
            print("MAVLinkTelemetry: setting mode to " + mode_name)
            self.mav.mav.set_mode_send(
                target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id,
            )
            self._flush()

# ----------------------------------------------------
# HELPER FUNCTIONS PORTED FROM ALERT SENDER
# ----------------------------------------------------
def _normalize_confidence(confidence):
    value = float(confidence)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("confidence must be a finite number")
    if value > 1.0 and value <= 100.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))

def _validate_coordinate(name, value, lower, upper):
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError(name + " must be a finite number")
    if value < lower or value > upper:
        raise ValueError(name + " outside valid range")
    return value

def _clean_target_class(target_class):
    text = str(target_class or "DRONE").upper()
    text = re.sub(r"[^A-Z0-9_]", "_", text)
    return text[:12] or "DRONE"

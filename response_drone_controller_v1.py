import os
import json
import time
import shutil
from datetime import datetime

# File Paths
ORDER_FILE = "/home/jiacdi/bordershield_ai/response_mission_order.json"
CONFIG_FILE = "/home/jiacdi/bordershield_ai/response_drone_config.json"
STATUS_FILE = "/home/jiacdi/bordershield_ai/response_drone_status.json"
LOG_FILE = "/home/jiacdi/bordershield_ai/response_drone_log.jsonl"

def load_config():
    """Load configuration dynamically, falling back to safe defaults if missing or corrupt."""
    defaults = {
        "simulation_mode": True,
        "safety_enable_real_flight": False,
        "check_interval_sec": 1.0
    }
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(defaults, f, indent=2)
        except Exception:
            pass
        return defaults
    
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("[WARN] Failed to read config file, using defaults. Error:", e)
        return defaults

def write_status(status, message, track_id=None):
    """Write current drone status to the status JSON file."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "track_id": track_id,
        "message": message
    }
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("[ERROR] Failed to write status file:", e)

def log_event(status, message, details=None):
    """Append a log entry to the JSONLines log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "message": message,
        "details": details or {}
    }
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print("[ERROR] Failed to write log:", e)

# ----------------------------------------------------
# FUTURE REAL MAVLINK CONTROL ABSTRACTION LAYER
# ----------------------------------------------------
def connect_response_vehicle():
    """Future: Connect to the Orange Cube / Pixhawk autopilot via serial."""
    print("[REAL FLIGHT] connect_response_vehicle() - Connecting to autopilot...")
    # mav = mavutil.mavlink_connection('/dev/ttyACM1', baud=115200)
    # return mav
    return "MOCK_MAV_CONN"

def set_guided(mav):
    """Future: Change flight controller mode to GUIDED."""
    print("[REAL FLIGHT] set_guided() - Sending GUIDED mode command...")

def arm_vehicle(mav):
    """Future: Send MAVLink Arm command to autopilot."""
    print("[REAL FLIGHT] arm_vehicle() - Sending ARM command...")

def takeoff(mav, target_altitude):
    """Future: Send Takeoff command to altitude AGL."""
    print(f"[REAL FLIGHT] takeoff() - Sending TAKEOFF command to {target_altitude}m...")

def goto_target(mav, lat, lon, alt):
    """Future: Send MAVLink reposition/mission item command."""
    print(f"[REAL FLIGHT] goto_target() - Sending GOTO GPS command: {lat:.6f}, {lon:.6f} at {alt:.1f}m...")

def hover(mav):
    """Future: Maintain position (Loiter/Guided hover)."""
    print("[REAL FLIGHT] hover() - Commands sent to hover over target.")

# ----------------------------------------------------
# MISSION DISPATCHER & DAEMON LOOP
# ----------------------------------------------------
def execute_mission(order, config):
    track_id = order.get("track_id")
    
    # 1. Validate order parameters
    order_type = order.get("order")
    status = order.get("status")
    
    lat = order.get("estimated_lat")
    lon = order.get("estimated_lon")
    alt = order.get("estimated_alt")
    
    if lat is None or lon is None or alt is None:
        target_loc = order.get("target_location", {})
        lat = target_loc.get("latitude") if lat is None else lat
        lon = target_loc.get("longitude") if lon is None else lon
        alt = target_loc.get("altitude") if alt is None else alt
        
    is_gps_valid = (lat is not None and lon is not None and not (lat == 0.0 and lon == 0.0))
    is_alt_valid = (alt is not None)
    
    print("\n>>> New Mission Order Received <<<")
    print(f"Track ID:        {track_id}")
    print(f"Order Action:    {order_type}")
    print(f"Target GPS:      {lat}, {lon}")
    print(f"Target Altitude: {alt}m AGL")
    
    if order_type != "GO_TO_TARGET_AND_HOVER" or status != "ready_for_response_drone":
        msg = f"Invalid order parameters: action={order_type}, status={status}"
        print(f"[REJECTED] {msg}")
        write_status("rejected_invalid_parameters", msg, track_id)
        log_event("rejected_invalid_parameters", msg, {"track_id": track_id})
        return False

    # 2. GPS Validity Gate check
    if not is_gps_valid or not is_alt_valid:
        msg = "GPS is invalid or altitude is unavailable. Arm and flight blocked."
        print(f"[BLOCKED] {msg}")
        write_status("blocked_invalid_gps", msg, track_id)
        log_event("blocked_invalid_gps", msg, {"track_id": track_id, "lat": lat, "lon": lon, "alt": alt})
        return False

    # 3. Execution based on simulation vs real mode
    sim_mode = config.get("simulation_mode", True)
    safety_real = config.get("safety_enable_real_flight", False)
    
    details = {
        "track_id": track_id,
        "lat": lat,
        "lon": lon,
        "alt": alt,
        "simulation_mode": sim_mode
    }
    
    if sim_mode:
        print("\n--- SIMULATION MODE EXECUTION STARTED ---")
        
        stages = [
            ("mission_received", "Mission received"),
            ("pre_arm_checks", "Pre-arm checks"),
            ("guided_mode", "Set GUIDED"),
            ("armed", "Arm"),
            ("takeoff", "Takeoff"),
            ("flying_to_target", "Fly to target"),
            ("hovering_over_target", "Hover over target")
        ]
        
        for state, desc in stages:
            print(f"  -> {desc}...")
            write_status(state, f"Simulated: {desc}", track_id)
            log_event(state, f"Simulated: {desc}", details)
            time.sleep(1.0) # simulated duration
            
        print("--- SIMULATION MISSION COMPLETED ---")
        return True
    else:
        print("\n--- REAL FLIGHT DISPATCH STARTED ---")
        if not safety_real:
            msg = "Real flight dispatch blocked: safety_enable_real_flight is set to False."
            print(f"[BLOCKED] {msg}")
            write_status("blocked_safety_disabled", msg, track_id)
            log_event("blocked_safety_disabled", msg, details)
            return False
            
        # Real flight commands execution path (future hardware linkage)
        try:
            write_status("pre_arm_checks", "Executing real flight pre-arm checks...", track_id)
            log_event("pre_arm_checks", "Executing real flight pre-arm checks...", details)
            
            mav = connect_response_vehicle()
            time.sleep(0.5)
            
            write_status("guided_mode", "Setting mode to GUIDED...", track_id)
            log_event("guided_mode", "Setting mode to GUIDED...", details)
            set_guided(mav)
            time.sleep(0.5)
            
            write_status("armed", "Arming vehicle...", track_id)
            log_event("armed", "Arming vehicle...", details)
            arm_vehicle(mav)
            time.sleep(0.5)
            
            write_status("takeoff", f"Taking off to {alt}m...", track_id)
            log_event("takeoff", f"Taking off to {alt}m...", details)
            takeoff(mav, alt)
            time.sleep(0.5)
            
            write_status("flying_to_target", "Flying to target...", track_id)
            log_event("flying_to_target", "Flying to target...", details)
            goto_target(mav, lat, lon, alt)
            time.sleep(0.5)
            
            write_status("hovering_over_target", "Hovering over target...", track_id)
            log_event("hovering_over_target", "Hovering over target...", details)
            hover(mav)
            
            print("--- REAL FLIGHT DISPATCH COMPLETED ---")
            return True
        except Exception as e:
            msg = f"Real flight failed due to exception: {e}"
            print(f"[FAIL] {msg}")
            write_status("flight_error", msg, track_id)
            log_event("flight_error", msg, details)
            return False

def main():
    print("=====================================================")
    print("BorderShield Response Drone Controller V1 Daemon")
    print("=====================================================")
    print("Log file: " + LOG_FILE)
    print("Status file: " + STATUS_FILE)
    print("Watching for new approved mission orders...")
    print("Press CTRL+C to stop.")
    print("=====================================================")
    
    # Initialize status file
    write_status("idle", "Waiting for mission order...")
    log_event("daemon_started", "Response Drone Controller daemon started successfully.")
    
    try:
        while True:
            config = load_config()
            interval = config.get("check_interval_sec", 1.0)
            
            if os.path.exists(ORDER_FILE):
                try:
                    with open(ORDER_FILE, "r") as f:
                        order = json.load(f)
                except Exception:
                    # File might be temporarily locked while being written
                    time.sleep(0.1)
                    continue
                
                success = execute_mission(order, config)
                
                # Archive the mission order file to prevent reprocessing it
                suffix = "processed" if success else "failed"
                archive_file = f"{ORDER_FILE}.{suffix}"
                try:
                    if os.path.exists(archive_file):
                        os.remove(archive_file)
                    shutil.move(ORDER_FILE, archive_file)
                    print(f"[INFO] Mission order archived to: {os.path.basename(archive_file)}")
                except Exception as e:
                    print("[ERROR] Failed to archive mission order file:", e)
                    try:
                        os.remove(ORDER_FILE)
                    except Exception:
                        pass
                        
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nResponse Drone Controller daemon stopped.")
        write_status("stopped", "Controller daemon stopped by user.")
        log_event("daemon_stopped", "Response Drone Controller daemon shut down.")

if __name__ == '__main__':
    main()

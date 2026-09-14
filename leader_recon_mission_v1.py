import os
import json
import time
import sys
from datetime import datetime

# ----------------------------------------------------
# CONFIGURATION AND FILE PATHS
# ----------------------------------------------------
EVENT_FILE = "/home/jiacdi/bordershield_ai/latest_target_event.json"
DECISION_FILE = "/home/jiacdi/bordershield_ai/latest_operator_decision.json"
ORDER_FILE = "/home/jiacdi/bordershield_ai/response_mission_order.json"
LOG_FILE = "/home/jiacdi/bordershield_ai/leader_recon_mission_log.jsonl"

# ----------------------------------------------------
# CLEAR STALE EVENTS ON STARTUP
# ----------------------------------------------------
if os.path.exists(EVENT_FILE):
    try:
        os.remove(EVENT_FILE)
        print("Cleaned up stale latest_target_event.json on startup.")
    except Exception as e:
        print("Warning: Could not remove stale latest_target_event.json:", e)

# Record startup time to ignore stale pre-startup events
STARTUP_TIME = datetime.now()

def parse_iso_timestamp(ts_str):
    """
    Robust ISO timestamp parser compatible with Python 3.6.
    Gracefully handles timezone offsets and formats with or without fractional seconds.
    """
    if "+" in ts_str:
        ts_str = ts_str.split("+")[0]
    elif "-" in ts_str and ts_str.count("-") == 3:
        ts_str = ts_str.rsplit("-", 1)[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            pass
    raise ValueError("Invalid ISO timestamp format: " + ts_str)

# Dynamic track decision tracking to avoid double-prompting the operator
track_decisions = {}

# ----------------------------------------------------
# SAFE ENCODING-RESISTANT INPUT METHOD
# ----------------------------------------------------
def safe_input(prompt):
    """
    Reads from sys.stdin.buffer (raw bytes) instead of standard input() text-mode wrapper.
    Decodes using UTF-8 with a replacement fallback to prevent any terminal-induced UnicodeDecodeError.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        # Read raw byte line from standard input buffer
        raw_bytes = sys.stdin.buffer.readline()
        # Decode ignoring/replacing invalid UTF-8 bytes to ensure stability over SSH terminal
        return raw_bytes.decode('utf-8', errors='replace').strip()
    except Exception as e:
        print("\n[WARN] Safe raw-input reader failed, trying fallback input parser... Error:", e)
        try:
            return input().strip()
        except Exception:
            return ""

print("=====================================================")
print("BorderShield Leader Recon Mission Flow Manager V1")
print("=====================================================")
print("Watching for target events...")
print("Log file: " + LOG_FILE)
print("Press CTRL+C to stop.")
print("=====================================================")

try:
    while True:
        if not os.path.exists(EVENT_FILE):
            time.sleep(0.5)
            continue

        try:
            # Force explicit UTF-8 decoding with error replacement when loading target event JSON
            with open(EVENT_FILE, "r", encoding="utf-8", errors="replace") as f:
                event = json.load(f)
        except Exception:
            # File might be temporarily locked or being rewritten by Terminal 1
            time.sleep(0.1)
            continue

        # ----------------------------------------------------
        # EVENT VALIDATION GATE
        # ----------------------------------------------------
        status = event.get("status")
        target_type = event.get("target_type")
        is_confirmed = event.get("is_confirmed", False)
        track_id = event.get("track_id")
        confidence = event.get("confidence", 0.0)

        # 1. Check target type, status, confirmation, confidence, and track_id
        if target_type != "DRONE" or status != "pending_approval" or not is_confirmed or track_id is None:
            time.sleep(0.5)
            continue

        if confidence < 25.0:  # Scale is 0-100 (e.g. 25.0 is 25%)
            time.sleep(0.5)
            continue

        # 2. Check event freshness (age must be < 3 seconds and must be post-startup)
        timestamp_str = event.get("event_created_at") or event.get("timestamp")
        try:
            event_time = parse_iso_timestamp(timestamp_str)
            age = (datetime.now() - event_time).total_seconds()
        except Exception:
            time.sleep(0.5)
            continue

        # Ignore events created before startup
        if event_time < STARTUP_TIME:
            time.sleep(0.5)
            continue

        # Ignore events older than 3 seconds
        if age > 3.0 or age < -3.0: # allow minor clock skew up to 3 seconds in future
            time.sleep(0.5)
            continue

        # 3. Ignore events already handled (duplicate track_id already processed)
        if track_id in track_decisions:
            time.sleep(0.5)
            continue

        # 4. Ignore events with stale track_id (must be active in current frame tracks)
        active_track_ids = [d.get("track_id") for d in event.get("detection_details", [])]
        if track_id not in active_track_ids:
            # Target is no longer tracked or active in the current frame
            time.sleep(0.5)
            continue

        # Extract event parameters
        confidence = event.get("confidence", 0.0)
        range_m = event.get("range_m", 0.0)
        bearing_deg = event.get("bearing_deg", 0.0)
        est_lat = event.get("estimated_lat")
        est_lon = event.get("estimated_lon")
        est_alt = event.get("estimated_alt")
        telemetry = event.get("leader_telemetry_used", {})

        is_target_gps_valid = (est_lat is not None and est_lon is not None and not (est_lat == 0.0 and est_lon == 0.0))

        print("\n" + "!"*53)
        print("HOSTILE DRONE DETECTED")
        print("!"*53)
        print("Track ID:        {}".format(track_id))
        print("Confidence:      {:.1f}%".format(confidence))
        print("Estimated Range: {:.1f} m".format(range_m))
        print("Bearing:         {:.1f} deg".format(bearing_deg))
        if is_target_gps_valid:
            print("Target GPS:      {:.6f}, {:.6f}".format(est_lat, est_lon))
            print("Target Altitude: {:.1f} m AGL".format(est_alt))
        else:
            print("Target GPS:      UNAVAILABLE (WAITING FOR GPS FIX)")
            print("Target Altitude: UNAVAILABLE")
        print("="*53)

        # Get operator input using the encoding-resistant input wrapper
        while True:
            decision = safe_input("Operator decision [approve/reject/skip]: ").lower()
            if decision == "approve" and not is_target_gps_valid:
                print("[ERROR] Cannot approve target: GPS is invalid / unavailable. Wait for GPS fix.")
                continue
            break

        if decision not in ["approve", "reject"]:
            print("[INFO] Skipped track ID {}. Will prompt again on next visibility.".format(track_id))
            time.sleep(1.0)
            continue

        # Record decision to prevent double-prompting for this track ID
        track_decisions[track_id] = decision

        # 1. Create operator decision JSON
        decision_data = {
            "timestamp": datetime.now().isoformat(),
            "frame_id": event.get("frame_id"),
            "targets": event.get("targets", []),
            "track_id": track_id,
            "decision": decision,
            "source": "operator"
        }
        
        try:
            with open(DECISION_FILE, "w", encoding="utf-8") as df:
                json.dump(decision_data, df, indent=2)
            print("[INFO] Operator decision saved: {}".format(decision.upper()))
        except Exception as e:
            print("[ERROR] Failed to save decision file:", e)

        # 2. If approved, create response mission order JSON
        if decision == "approve":
            order_data = {
                "order": "GO_TO_TARGET_AND_HOVER",
                "status": "ready_for_response_drone",
                "track_id": track_id,
                "confidence": confidence,
                "range_m": range_m,
                "bearing_deg": bearing_deg,
                "target_lat": est_lat,
                "target_lon": est_lon,
                "target_alt": est_alt,
                "estimated_lat": est_lat,
                "estimated_lon": est_lon,
                "estimated_alt": est_alt,
                "timestamp": datetime.now().isoformat(),
                "source": "leader_recon",
                # Also keep nested structures for backward compatibility
                "target_location": {
                    "latitude": est_lat,
                    "longitude": est_lon,
                    "altitude": est_alt
                },
                "target_details": {
                    "target_type": "DRONE",
                    "confidence": confidence,
                    "track_id": track_id,
                    "range_m": range_m,
                    "bearing_deg": bearing_deg
                }
            }
            try:
                with open(ORDER_FILE, "w", encoding="utf-8") as of:
                    json.dump(order_data, of, indent=2)
                print("[SUCCESS] Response mission order created: response_mission_order.json")
            except Exception as e:
                print("[ERROR] Failed to save response mission order:", e)

        # 3. Log to session leader_recon_mission_log.jsonl
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_details": event,
            "decision": decision,
            "action": "mission_order_created" if decision == "approve" else "patrol_continued"
        }
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print("[ERROR] Failed to write to log file:", e)

        print("[INFO] Resuming border patrol surveillance...")
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nMission Flow Manager stopped by operator.")

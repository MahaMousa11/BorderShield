import os
import sys
import time
import pty
import tty
import threading
import fcntl
from pymavlink.dialects.v20.ardupilotmega import MAVLink

# Add current path to import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mavlink_telemetry import MAVLinkTelemetry
from scout_mavlink_alert import ScoutMAVLinkAlertSender
from scout_auto_pause_controller import ScoutAutoPauseController

class FDWrapper:
    def __init__(self, fd):
        self.fd = fd
    def write(self, buf):
        try:
            return os.write(self.fd, buf)
        except OSError:
            return 0
    def read(self, n):
        try:
            return os.read(self.fd, n)
        except OSError:
            return b''

def mock_autopilot_loop(master_fd, stop_event, received_messages):
    """Generates mock ArduPilot telemetry packets and logs received companion computer commands."""
    # Set master_fd to non-blocking
    fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    # Create MAVLink encoder/decoder
    mav = MAVLink(FDWrapper(master_fd))
    
    # Configure autopilot system and component ID
    mav.srcSystem = 1
    mav.srcComponent = 1
    
    print("[Autopilot] Mock autopilot thread started.")
    while not stop_event.is_set():
        try:
            # 1. Send HEARTBEAT
            mav.heartbeat_send(
                2,    # type: MAV_TYPE_QUADROTOR
                3,    # autopilot: MAV_AUTOPILOT_ARDUPILOTMEGA
                193,  # base_mode
                3,    # custom_mode: Copter Mode 3 = AUTO
                4,    # system_status: MAV_STATE_ACTIVE
                3     # MAVLink version
            )
            
            # 2. Send GLOBAL_POSITION_INT
            mav.global_position_int_send(
                int(time.monotonic() * 1000) & 0xFFFFFFFF,
                328974000,   # lat
                -1172024000,  # lon
                50000,       # alt
                10000,       # relative_alt
                0,           # vx
                0,           # vy
                0,           # vz
                4500         # hdg
            )
            
            # 3. Send GPS_RAW_INT
            mav.gps_raw_int_send(
                int(time.monotonic() * 1000000) & 0xFFFFFFFFFFFFFFFF,
                3,           # fix_type: 3D Fix
                328974000,   # lat
                -1172024000,  # lon
                50000,       # alt
                100,         # eph
                100,         # epv
                9999,        # vel
                9999,        # cog
                12           # satellites_visible
            )
            
            # 4. Send ATTITUDE
            mav.attitude_send(
                int(time.monotonic() * 1000) & 0xFFFFFFFF,
                0.0349,      # roll (~2 deg)
                -0.0873,     # pitch (~-5 deg)
                0.7854,      # yaw (~45 deg)
                0.0,         # rollspeed
                0.0,         # pitchspeed
                0.0          # yawspeed
            )
            
            # Read incoming data from telemetry service
            try:
                data = os.read(master_fd, 4096)
                if data:
                    for b in data:
                        # Feed to parser
                        msg = mav.parse_char(bytes([b]))
                        if msg:
                            mtype = msg.get_type()
                            print(f"[Autopilot Received] {mtype}")
                            received_messages.append(msg.to_dict())
            except BlockingIOError:
                pass
                
        except Exception as e:
            print("[Autopilot Error]:", e)
            break
            
        time.sleep(0.1)
        
    print("[Autopilot] Thread stopped.")

def main():
    print("=== BorderShield Shared MAVLink Architecture Verification ===")
    
    # Create virtual serial port pair
    master_fd, slave_fd = pty.openpty()
    
    # Put slave pseudo-terminal into raw binary mode to disable echo and CR/LF mapping
    tty.setraw(slave_fd)
    
    slave_name = os.ttyname(slave_fd)
    print(f"Created virtual tty pair: Master FD={master_fd} <-> Slave Path={slave_name}")
    
    stop_event = threading.Event()
    received_messages = []
    
    # Start mock autopilot thread
    ap_thread = threading.Thread(
        target=mock_autopilot_loop,
        args=(master_fd, stop_event, received_messages),
        daemon=True
    )
    ap_thread.start()
    
    time.sleep(0.5)  # Allow autopilot thread to start up
    
    # ----------------------------------------------------
    # TEST 1: Initialize and Start MAVLinkTelemetry
    # ----------------------------------------------------
    print("\n--- TEST 1: Initializing MAVLinkTelemetry Core ---")
    telemetry = MAVLinkTelemetry(connection_string=slave_name, baud=115200)
    telemetry.start()
    
    # Wait for telemetry connection to be active
    print("Waiting for telemetry service to connect and parse heartbeats...")
    connected = False
    for _ in range(20):
        tdata = telemetry.get_telemetry()
        if tdata["connected"] and tdata["gps_fix"] > 1:
            connected = True
            print("MAVLinkTelemetry connection established successfully!")
            print("Parsed Telemetry:", tdata)
            break
        time.sleep(0.5)
        
    if not connected:
        print("ERROR: Telemetry service failed to connect or parse simulated streams.")
        stop_event.set()
        telemetry.stop()
        return 1
        
    # ----------------------------------------------------
    # TEST 2: Inject Telemetry into ScoutMAVLinkAlertSender
    # ----------------------------------------------------
    print("\n--- TEST 2: Injecting Telemetry into Alert Sender ---")
    alert_sender = ScoutMAVLinkAlertSender(telemetry)
    alert_sender.connect(heartbeat_timeout=3.0)
    alert_sender.start_heartbeat()
    
    print("Sending fake detection alert at target location...")
    lat_tgt = 32.897452
    lon_tgt = -117.202356
    alt_tgt = 45.1
    confidence = 0.885
    expected_pct = int(round(confidence * 100.0))
    expected_text = "BS,{:.7f},{:.7f},{:d},DRONE".format(lat_tgt, lon_tgt, expected_pct)
    
    alert_sender.send_detection_alert(lat_tgt, lon_tgt, alt_tgt, confidence, "DRONE")
    time.sleep(1.0)  # Wait for autopilot to parse/process messages
    
    # Verify autopilot received STATUSTEXT and NAMED_VALUEs
    statustext_received = False
    tgt_lat_received = False
    tgt_lon_received = False
    tgt_conf_received = False
    
    for msg in received_messages:
        mtype = msg.get("mavpackettype")
        if mtype == "STATUSTEXT":
            text = msg.get("text")
            print("  Autopilot parsed STATUSTEXT:", text)
            if expected_text in text:
                statustext_received = True
        elif mtype == "NAMED_VALUE_INT":
            name = msg.get("name")
            value = msg.get("value")
            print(f"  Autopilot parsed NAMED_VALUE_INT: {name} = {value}")
            if name == "TGT_LAT" and value == int(round(lat_tgt * 1e7)):
                tgt_lat_received = True
            if name == "TGT_LON" and value == int(round(lon_tgt * 1e7)):
                tgt_lon_received = True
        elif mtype == "NAMED_VALUE_FLOAT":
            name = msg.get("name")
            value = msg.get("value")
            print(f"  Autopilot parsed NAMED_VALUE_FLOAT: {name} = {value:.4f}")
            if name == "TGT_CONF" and abs(value - confidence) < 0.01:
                tgt_conf_received = True
                
    test2_passed = statustext_received and tgt_lat_received and tgt_lon_received and tgt_conf_received
    print("TEST 2 RESULT:", "PASSED" if test2_passed else "FAILED")
    
    # ----------------------------------------------------
    # TEST 3: Inject Telemetry into ScoutAutoPauseController
    # ----------------------------------------------------
    print("\n--- TEST 3: Injecting Telemetry into Auto Pause Controller ---")
    auto_pause_mode_state = {"mode": None}
    auto_pause_controller = ScoutAutoPauseController(
        telemetry=telemetry,
        alert_sender=alert_sender,
        hold_mode="LOITER",
        return_mode="AUTO",
        hold_seconds=2,
        cooldown_sec=5,
        dry_run=False,
        current_mode_provider=lambda: auto_pause_mode_state.get("mode")
    )
    auto_pause_controller.connect()
    
    # Verify we can read the current flight mode (AUTO) from the telemetry cache
    mode = auto_pause_controller.get_current_mode()
    print(f"Auto Pause Controller query get_current_mode() = {mode}")
    mode_ok = (mode == "AUTO")
    
    # Clear received message history to catch mode changes
    received_messages.clear()
    
    # Trigger set_mode LOITER
    print("Requesting mode change to LOITER...")
    auto_pause_controller.set_mode("LOITER")
    time.sleep(1.0)
    
    set_mode_received = False
    for msg in received_messages:
        if msg.get("mavpackettype") == "SET_MODE":
            custom_mode = msg.get("custom_mode")
            # LOITER custom mode for Copter is typically 5
            print(f"  Autopilot parsed SET_MODE custom_mode = {custom_mode}")
            if custom_mode == 5:
                set_mode_received = True
                
    test3_passed = mode_ok and set_mode_received
    print("TEST 3 RESULT:", "PASSED" if test3_passed else "FAILED")
    
    # ----------------------------------------------------
    # TEARDOWN
    # ----------------------------------------------------
    print("\nShutting down verification test...")
    alert_sender.close()
    auto_pause_controller.close()
    telemetry.stop()
    stop_event.set()
    
    overall_passed = test2_passed and test3_passed
    print("\n====================================================")
    print("VERIFICATION SUMMARY:", "ALL TESTS PASSED!" if overall_passed else "TEST FAILURE DETECTED!")
    print("====================================================")
    return 0 if overall_passed else 1

if __name__ == "__main__":
    sys.exit(main())

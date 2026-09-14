import json
import time
import os
from datetime import datetime

EVENT_FILE = "/home/jiacdi/bordershield_ai/latest_target_event.json"
DECISION_FILE = "/home/jiacdi/bordershield_ai/latest_operator_decision.json"

last_frame_id = None

print("BorderShield Mission Manager V1 started")
print("Waiting for AI target events...")
print("Press CTRL+C to stop")

try:
    while True:
        if not os.path.exists(EVENT_FILE):
            time.sleep(1)
            continue

        try:
            with open(EVENT_FILE, "r") as f:
                event = json.load(f)
        except Exception:
            time.sleep(0.5)
            continue

        frame_id = event.get("frame_id")
        targets = event.get("targets", [])
        status = event.get("status")

        if frame_id == last_frame_id or status != "pending_approval" or not targets:
            time.sleep(1)
            continue

        last_frame_id = frame_id

        print("\n" + "=" * 55)
        print("NEW BORDER TARGET DETECTED")
        print("Time:", event.get("timestamp"))
        print("Frame:", frame_id)
        print("Targets:", ", ".join(targets))
        print("Drone best confidence:", event.get("drone_best_confidence"), "%")
        print("=" * 55)

        decision = input("Operator decision [approve/reject/skip]: ").strip().lower()

        if decision not in ["approve", "reject"]:
            decision = "skip"

        output = {
            "timestamp": datetime.now().isoformat(),
            "frame_id": frame_id,
            "targets": targets,
            "decision": decision,
            "source": "operator"
        }

        with open(DECISION_FILE, "w") as f:
            json.dump(output, f, indent=2)

        print("Decision saved:", decision)

except KeyboardInterrupt:
    print("\nMission Manager stopped")

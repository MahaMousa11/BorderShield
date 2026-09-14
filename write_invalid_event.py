import json
from datetime import datetime

event = {
    "frame_id": 42,
    "timestamp": datetime.now().isoformat(),
    "targets": ["drone"],
    "drone_best_confidence": 85.0,
    "status": "pending_approval",
    "is_confirmed": True,
    "track_status": "confirmed",
    "source": "leader_recon_ai",
    "event_type": "DRONE_DETECTED",
    "target_type": "DRONE",
    "confidence": 85.0,
    "track_id": 1,
    "range_m": 50.0,
    "bearing_deg": 12.0,
    "estimated_lat": 0.0,
    "estimated_lon": 0.0,
    "estimated_alt": 0.0,
    "event_created_at": datetime.now().isoformat(),
    "detection_details": [{"track_id": 1, "confidence": 85.0}]
}

with open("/home/jiacdi/bordershield_ai/latest_target_event.json", "w") as f:
    json.dump(event, f, indent=2)

print("Fresh invalid GPS event written.")

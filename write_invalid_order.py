import json
from datetime import datetime

order = {
  "order": "GO_TO_TARGET_AND_HOVER",
  "status": "ready_for_response_drone",
  "track_id": 43,
  "confidence": 85.0,
  "range_m": 35.0,
  "bearing_deg": 14.5,
  "estimated_lat": 0.0,
  "estimated_lon": 0.0,
  "estimated_alt": 15.0,
  "timestamp": datetime.now().isoformat(),
  "source": "leader_recon"
}

with open("/home/jiacdi/bordershield_ai/response_mission_order.json", "w") as f:
    json.dump(order, f, indent=2)

print("Fresh invalid response mission order written.")

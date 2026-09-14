import json
from datetime import datetime

event = {
  "frame_id": 1236,
  "timestamp": datetime.now().isoformat(),
  "targets": ["DRONE 88.5%"],
  "drone_best_confidence": 88.5,
  "status": "pending_approval",
  "is_confirmed": True,
  "event_type": "DRONE_DETECTED",
  "target_type": "DRONE",
  "confidence": 88.5,
  "track_id": 102,
  "range_m": 35.6,
  "bearing_deg": 12.4,
  "estimated_lat": 32.897452,
  "estimated_lon": -117.202356,
  "estimated_alt": 45.1,
  "leader_telemetry_used": {
    "latitude": 32.8974,
    "longitude": -117.2024,
    "altitude": 50.0,
    "heading": 45.0,
    "pitch": -5.0,
    "roll": 2.0
  },
  "detection_details": [
    {
      "track_id": 102,
      "confidence": 88.5,
      "bbox": [100, 100, 50, 50],
      "is_confirmed": True,
      "localization": {
        "distance": 35.6,
        "relative_x_body": 35.0,
        "relative_y_body": 2.0,
        "relative_z_body": 5.0,
        "relative_x_ned": 25.0,
        "relative_y_ned": 25.0,
        "relative_z_ned": 5.0,
        "bearing_body_deg": 12.4,
        "bearing_absolute_deg": 45.0,
        "elevation_body_deg": -8.0,
        "elevation_absolute_deg": -8.0,
        "gps": {
          "latitude": 32.897452,
          "longitude": -117.202356,
          "altitude": 45.1
        }
      }
    }
  ]
}

with open("/home/jiacdi/bordershield_ai/latest_target_event.json", "w") as f:
    json.dump(event, f, indent=2)
print("Mock event 101 saved to latest_target_event.json")

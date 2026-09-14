import json
import datetime

try:
    with open('/home/jiacdi/bordershield_ai/latest_target_event.json', 'r') as f:
        d = json.load(f)
    print("Event timestamp:", d['timestamp'])
except Exception as e:
    print("Failed to open latest_target_event.json:", e)

print("System current time:", datetime.datetime.now().isoformat())

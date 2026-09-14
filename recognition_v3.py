import cv2
import time
import os
import json
from datetime import datetime

CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant",
    "sheep", "sofa", "train", "tvmonitor"
]

TARGETS = ["person", "car", "bus", "motorbike"]

CONFIDENCE_THRESHOLD = 0.60
ALERT_COOLDOWN_SECONDS = 8

def classify_threat(target, confidence):
    confidence_percent = confidence * 100

    if target == "person":
        return {
            "category": "suspicious_person",
            "threat_level": "MEDIUM" if confidence_percent < 90 else "HIGH",
            "recommended_action": "notify_operator_and_continue_monitoring"
        }

    if target in ["car", "bus", "motorbike"]:
        return {
            "category": "ground_vehicle",
            "threat_level": "LOW" if confidence_percent < 85 else "MEDIUM",
            "recommended_action": "track_vehicle_and_log_evidence"
        }

    return {
        "category": "unknown",
        "threat_level": "LOW",
        "recommended_action": "log_only"
    }

os.makedirs("alerts_v3/images", exist_ok=True)

csv_log = "alerts_v3/detection_log.csv"
json_log = "alerts_v3/mission_events.jsonl"
summary_log = "alerts_v3/alert_summary.txt"

if not os.path.exists(csv_log):
    with open(csv_log, "w") as f:
        f.write("timestamp,frame,target,confidence,category,threat_level,recommended_action,image\n")

net = cv2.dnn.readNetFromCaffe(
    "person_detection_model/deploy.prototxt",
    "person_detection_model/mobilenet_iter_73000.caffemodel"
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

last_alert_time = {}
frame_count = 0
event_id = 0

print("BorderShield Recognition v3 started...")
print("Targets:", TARGETS)
print("Threat classification: ENABLED")
print("Mission JSON events: ENABLED")
print("CTRL+C to stop")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Failed to read frame")
            break

        frame_count += 1
        h, w = frame.shape[:2]

        blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()

        now = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        seen_targets = []

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            class_id = int(detections[0, 0, i, 1])
            target = CLASSES[class_id]

            if confidence >= CONFIDENCE_THRESHOLD and target in TARGETS:
                seen_targets.append((target, confidence))

                last_time = last_alert_time.get(target, 0)
                if now - last_time < ALERT_COOLDOWN_SECONDS:
                    continue

                last_alert_time[target] = now
                event_id += 1

                threat = classify_threat(target, confidence)

                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                x1, y1, x2, y2 = box.astype("int")

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = "{} {:.1f}% | {}".format(
                    target.upper(), confidence * 100, threat["threat_level"]
                )
                cv2.putText(frame, label, (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

                image_path = "alerts_v3/images/{}_event{}_{}.jpg".format(
                    timestamp, event_id, target
                )
                cv2.imwrite(image_path, frame)

                event = {
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "frame": frame_count,
                    "target": target,
                    "confidence": round(confidence * 100, 2),
                    "category": threat["category"],
                    "threat_level": threat["threat_level"],
                    "recommended_action": threat["recommended_action"],
                    "image": image_path,
                    "source": "jetson_nano_camera",
                    "system": "BorderShield Recognition v3"
                }

                with open(json_log, "a") as f:
                    f.write(json.dumps(event) + "\n")

                with open(csv_log, "a") as f:
                    f.write("{},{},{},{:.2f},{},{},{},{}\n".format(
                        timestamp,
                        frame_count,
                        target,
                        confidence * 100,
                        threat["category"],
                        threat["threat_level"],
                        threat["recommended_action"],
                        image_path
                    ))

                with open(summary_log, "a") as f:
                    f.write("[{}] EVENT {} | {} | {:.2f}% | {} | Action: {} | {}\n".format(
                        timestamp,
                        event_id,
                        target.upper(),
                        confidence * 100,
                        threat["threat_level"],
                        threat["recommended_action"],
                        image_path
                    ))

                print("EVENT", event_id, "|", target.upper(), "|",
                      round(confidence * 100, 2), "% |",
                      threat["threat_level"], "|",
                      threat["recommended_action"])

        if seen_targets:
            readable = ["{} {:.1f}%".format(t.upper(), c * 100) for t, c in seen_targets]
            print("Frame", frame_count, "| seen:", ", ".join(readable))
        else:
            print("Frame", frame_count, "| clear")

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped by user")

cap.release()
print("Recognition v3 stopped")
print("Total mission events:", event_id)

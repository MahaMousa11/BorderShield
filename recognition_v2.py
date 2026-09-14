import cv2
import time
import os
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

last_alert_time = {}

os.makedirs("alerts_v2", exist_ok=True)

log_file = "alerts_v2/detection_log.csv"
summary_file = "alerts_v2/alert_summary.txt"

if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("timestamp,frame,target,confidence,image\n")

net = cv2.dnn.readNetFromCaffe(
    "person_detection_model/deploy.prototxt",
    "person_detection_model/mobilenet_iter_73000.caffemodel"
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

frame_count = 0
total_alerts = 0

print("BorderShield Recognition v2 started...")
print("Targets:", TARGETS)
print("Cooldown:", ALERT_COOLDOWN_SECONDS, "seconds")
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

        frame_targets = []

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            class_id = int(detections[0, 0, i, 1])
            target = CLASSES[class_id]

            if confidence >= CONFIDENCE_THRESHOLD and target in TARGETS:
                frame_targets.append((target, confidence))

                last_time = last_alert_time.get(target, 0)

                if now - last_time < ALERT_COOLDOWN_SECONDS:
                    continue

                last_alert_time[target] = now
                total_alerts += 1

                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                x1, y1, x2, y2 = box.astype("int")

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = "{} {:.1f}%".format(target.upper(), confidence * 100)
                cv2.putText(frame, label, (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                image_name = "alerts_v2/{}_alert{}_{}.jpg".format(
                    timestamp, total_alerts, target
                )

                cv2.imwrite(image_name, frame)

                with open(log_file, "a") as f:
                    f.write("{},{},{},{:.2f},{}\n".format(
                        timestamp, frame_count, target,
                        confidence * 100, image_name
                    ))

                with open(summary_file, "a") as f:
                    f.write("[{}] ALERT {} | Confidence {:.2f}% | Frame {} | Image {}\n".format(
                        timestamp, target.upper(),
                        confidence * 100, frame_count, image_name
                    ))

                print("ALERT:", target.upper(), round(confidence * 100, 2), "%", "| saved:", image_name)

        if frame_targets:
            readable = ["{} {:.1f}%".format(t.upper(), c * 100) for t, c in frame_targets]
            print("Frame", frame_count, "| seen:", ", ".join(readable))
        else:
            print("Frame", frame_count, "| clear")

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped by user")

cap.release()

print("Recognition v2 stopped")
print("Total alerts:", total_alerts)

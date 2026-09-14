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

os.makedirs("alerts", exist_ok=True)

net = cv2.dnn.readNetFromCaffe(
    "person_detection_model/deploy.prototxt",
    "person_detection_model/mobilenet_iter_73000.caffemodel"
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

log_file = "alerts/detection_log.csv"

if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("timestamp,frame,target,confidence,image\n")

frame_count = 0
print("BorderShield Recognition v1 started...")
print("Targets:", TARGETS)
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

        detected_any = False
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            class_id = int(detections[0, 0, i, 1])
            target = CLASSES[class_id]

            if confidence >= 0.60 and target in TARGETS:
                detected_any = True

                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                x1, y1, x2, y2 = box.astype("int")

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = "{} {:.1f}%".format(target.upper(), confidence * 100)
                cv2.putText(frame, label, (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                image_name = "alerts/{}_frame{}_{}.jpg".format(timestamp, frame_count, target)
                cv2.imwrite(image_name, frame)

                with open(log_file, "a") as f:
                    f.write("{},{},{},{:.2f},{}\n".format(
                        timestamp, frame_count, target, confidence * 100, image_name
                    ))

                print("ALERT:", target.upper(), round(confidence * 100, 2), "%", "| saved:", image_name)

        if not detected_any:
            print("Frame", frame_count, "| clear")

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped by user")

cap.release()
print("Recognition v1 stopped")

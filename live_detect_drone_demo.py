import cv2
import time

CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant",
    "sheep", "sofa", "train", "tvmonitor"
]

TARGETS = ["person", "car", "bus", "motorbike", "aeroplane"]

net = cv2.dnn.readNetFromCaffe(
    "person_detection_model/deploy.prototxt",
    "person_detection_model/mobilenet_iter_73000.caffemodel"
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

frame_count = 0

print("BorderShield AI Recognition started...")
print("Detecting:", TARGETS)
print("Press CTRL+C to stop")

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

        start = time.time()
        detections = net.forward()
        elapsed = time.time() - start

        alerts = []

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            class_id = int(detections[0, 0, i, 1])
            label_name = CLASSES[class_id]

            if confidence > 0.45 and label_name in TARGETS:
                box = detections[0, 0, i, 3:7] * [w, h, w, h]
                x1, y1, x2, y2 = box.astype("int")

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                text = "{} {:.1f}%".format(("POSSIBLE_DRONE" if label_name == "aeroplane" else label_name.upper()), confidence * 100)
                cv2.putText(frame, text, (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                alerts.append("{} {:.1f}%".format(("POSSIBLE_DRONE" if label_name == "aeroplane" else label_name.upper()), confidence * 100))

        if alerts:
            print("Frame", frame_count, "|", ", ".join(alerts), "|", round(elapsed, 3), "sec")
        else:
            print("Frame", frame_count, "| No target |", round(elapsed, 3), "sec")

        cv2.imwrite("latest_detection.jpg", frame)
        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped by user")

cap.release()
print("Recognition stopped")

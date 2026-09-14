import cv2
import time

CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant",
    "sheep", "sofa", "train", "tvmonitor"
]

net = cv2.dnn.readNetFromCaffe(
    "person_detection_model/deploy.prototxt",
    "person_detection_model/mobilenet_iter_73000.caffemodel"
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

ret, frame = cap.read()
cap.release()

if not ret:
    print("ERROR: Could not capture frame")
    exit()

h, w = frame.shape[:2]
blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
net.setInput(blob)

start = time.time()
detections = net.forward()
elapsed = time.time() - start

found = False

for i in range(detections.shape[2]):
    confidence = detections[0, 0, i, 2]
    class_id = int(detections[0, 0, i, 1])

    if confidence > 0.45 and CLASSES[class_id] == "person":
        found = True
        box = detections[0, 0, i, 3:7] * [w, h, w, h]
        x1, y1, x2, y2 = box.astype("int")

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = "PERSON {:.1f}%".format(confidence * 100)
        cv2.putText(frame, label, (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        print("PERSON DETECTED:", round(confidence * 100, 2), "%")

if not found:
    print("No person detected")

print("Inference time:", round(elapsed, 3), "seconds")
cv2.imwrite("person_detection_result.jpg", frame)
print("Saved person_detection_result.jpg")

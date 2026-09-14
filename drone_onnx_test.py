import cv2
import numpy as np

MODEL = "models/drone_yolov5/best.onnx"
IMAGE = "test_drone.jpg"

CONF_THRES = 0.10
INPUT_SIZE = 640

net = cv2.dnn.readNetFromONNX(MODEL)

img = cv2.imread(IMAGE)
if img is None:
    print("ERROR: image not found")
    exit()

h0, w0 = img.shape[:2]

blob = cv2.dnn.blobFromImage(img, 1/255.0, (INPUT_SIZE, INPUT_SIZE), swapRB=True, crop=False)
net.setInput(blob)

out = net.forward()
print("Output shape:", out.shape)

detections = out[0]
found = False

for det in detections:
    cx, cy, w, h, obj_conf, class_conf = det[:6]
    conf = obj_conf * class_conf

    if conf >= CONF_THRES:
        found = True

        x1 = int((cx - w / 2) * w0 / INPUT_SIZE)
        y1 = int((cy - h / 2) * h0 / INPUT_SIZE)
        x2 = int((cx + w / 2) * w0 / INPUT_SIZE)
        y2 = int((cy + h / 2) * h0 / INPUT_SIZE)

        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, "DRONE {:.1f}%".format(conf * 100),
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        print("DRONE DETECTED:", round(conf * 100, 2), "%")

if not found:
    print("No drone detected")

cv2.imwrite("drone_onnx_result.jpg", img)
print("Saved drone_onnx_result.jpg")

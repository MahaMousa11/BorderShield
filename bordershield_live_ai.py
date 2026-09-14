import cv2
import time

CAM_INDEX = 0
CONF_TH = 0.35
NMS_TH = 0.4
INPUT_SIZE = 416

COCO_CFG = "/home/jiacdi/yolo_rtsp/models/yolov3-tiny.cfg"
COCO_WEIGHTS = "/home/jiacdi/yolo_rtsp/models/yolov3-tiny.weights"
COCO_NAMES = "/home/jiacdi/yolo_rtsp/models/coco.names"

DRONE_CFG = "/home/jiacdi/darknet/cfg/yolov3-tiny-drone.cfg"
DRONE_WEIGHTS = "/home/jiacdi/darknet/backup/yolov3-tiny-drone_best.weights"
DRONE_NAMES = "/home/jiacdi/darknet/data/obj.names"

WATCH_CLASSES = {
    "person": "PERSON",
    "car": "VEHICLE",
    "truck": "VEHICLE",
    "bus": "VEHICLE",
    "motorbike": "VEHICLE",
    "bicycle": "VEHICLE",
}

def load_names(path):
    with open(path, "r") as f:
        return [x.strip() for x in f.readlines() if x.strip()]

def output_layers(net):
    names = net.getLayerNames()
    return [names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

def detect(net, names, frame, prefix_filter=None):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (INPUT_SIZE, INPUT_SIZE), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers(net))

    boxes, confs, labels = [], [], []

    for out in outs:
        for det in out:
            scores = det[5:]
            class_id = int(scores.argmax())
            conf = float(scores[class_id])

            if conf < CONF_TH:
                continue

            label = names[class_id]

            if prefix_filter and label not in prefix_filter:
                continue

            cx, cy, bw, bh = det[0:4]
            x = int((cx - bw / 2) * w)
            y = int((cy - bh / 2) * h)
            bw = int(bw * w)
            bh = int(bh * h)

            boxes.append([x, y, bw, bh])
            confs.append(conf)
            labels.append(label)

    idxs = cv2.dnn.NMSBoxes(boxes, confs, CONF_TH, NMS_TH)

    results = []
    if len(idxs) > 0:
        for i in idxs.flatten():
            results.append((labels[i], confs[i], boxes[i]))

    return results

print("[INFO] Loading COCO model...")
coco_names = load_names(COCO_NAMES)
coco_net = cv2.dnn.readNetFromDarknet(COCO_CFG, COCO_WEIGHTS)
coco_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)

print("[INFO] Loading DRONE model...")
drone_names = load_names(DRONE_NAMES)
drone_net = cv2.dnn.readNetFromDarknet(DRONE_CFG, DRONE_WEIGHTS)
drone_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)

print("[INFO] Opening camera...")
cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    raise RuntimeError("Camera could not be opened")

print("[INFO] BorderShield Live AI started")
print("[INFO] Detecting: PERSON / VEHICLE / DRONE")
print("[INFO] Press Ctrl+C to stop")

frame_id = 0
last_print = 0

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[WARN] Failed to read frame")
            time.sleep(0.2)
            continue

        frame_id += 1
        start = time.time()

        coco_results = detect(coco_net, coco_names, frame, prefix_filter=WATCH_CLASSES.keys())
        drone_results = detect(drone_net, drone_names, frame)

        events = []

        for label, conf, box in coco_results:
            target_type = WATCH_CLASSES.get(label, label.upper())
            events.append((target_type, label, conf, box))

        for label, conf, box in drone_results:
            events.append(("DRONE", label, conf, box))

        now = time.time()
        if events or now - last_print > 2:
            print("=" * 55)
            print("Frame:", frame_id, "| inference_time:", round(time.time() - start, 2), "sec")

            if not events:
                print("No target")
            else:
                for target_type, label, conf, box in events:
                    x, y, w, h = box
                    print("{} DETECTED | class={} | conf={:.1f}% | box=({}, {}, {}, {})".format(
                        target_type, label, conf * 100, x, y, w, h
                    ))

            last_print = now

except KeyboardInterrupt:
    print("\n[INFO] Stopped by user")

finally:
    cap.release()

import os
import sys
import time
import cv2
import numpy as np

# Load config/constants from main script
sys.path.append("/home/jiacdi/darknet")
import darknet

# Config paths
CAFFE_PROTO = "/home/jiacdi/bordershield_ai/person_detection_model/deploy.prototxt"
CAFFE_WEIGHTS = "/home/jiacdi/bordershield_ai/person_detection_model/mobilenet_iter_73000.caffemodel"
DRONE_CFG = "/home/jiacdi/darknet/cfg/yolov3-tiny-drone.cfg"
DRONE_WEIGHTS = "/home/jiacdi/darknet/backup/yolov3-tiny-drone_best.weights"
DRONE_NAMES = "/home/jiacdi/darknet/data/obj.names"
DRONE_DATA = "/home/jiacdi/darknet/data/obj.data"

# Initialize nets
print("Initializing Caffe SSD...")
net_ssd = cv2.dnn.readNetFromCaffe(CAFFE_PROTO, CAFFE_WEIGHTS)
net_ssd.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
net_ssd.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

print("Initializing Darknet GPU...")
orig_cwd = os.getcwd()
os.chdir("/home/jiacdi/darknet")
net_yolo, class_names, _ = darknet.load_network(DRONE_CFG, DRONE_DATA, DRONE_WEIGHTS, batch_size=1)
os.chdir(orig_cwd)

net_w = darknet.network_width(net_yolo)
net_h = darknet.network_height(net_yolo)
darknet_image = darknet.make_image(net_w, net_h, 3)

# Video capture
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Helper for letterbox
def letterbox_image(image, target_size=(416, 416)):
    ih, iw = image.shape[:2]
    w, h = target_size
    scale = min(w / iw, h / ih)
    nw = int(iw * scale)
    nh = int(ih * scale)
    image_resized = cv2.resize(image, (nw, nh))
    canvas = np.full((h, w, 3), 127, dtype=np.uint8)
    dx = (w - nw) // 2
    dy = (h - nh) // 2
    canvas[dy:dy+nh, dx:dx+nw] = image_resized
    return canvas, scale, dx, dy

# Warmup both networks
print("Warming up models...")
ret, frame = cap.read()
if ret:
    # SSD
    blob_ssd = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
    net_ssd.setInput(blob_ssd)
    net_ssd.forward()
    
    # YOLO
    lb, _, _, _ = letterbox_image(frame, (net_w, net_h))
    img_rgb = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB)
    darknet.copy_image_from_bytes(darknet_image, img_rgb.tobytes())
    darknet.predict_image(net_yolo, darknet_image)

print("Starting 100 frame benchmark...")

times_capture = []
times_ssd = []
times_yolo = []
times_tracking = []
times_loc = []
times_hud = []
times_total = []

for frame_idx in range(1, 101):
    t_start = time.time()
    
    # 1. Camera Capture
    t0 = time.time()
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        continue
    times_capture.append(time.time() - t0)
    
    h, w = frame.shape[:2]
    
    # 2. SSD Inference
    t0 = time.time()
    blob_ssd = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
    net_ssd.setInput(blob_ssd)
    detections = net_ssd.forward()
    times_ssd.append(time.time() - t0)
    
    # 3. YOLO Inference
    t0 = time.time()
    letterboxed_img, lb_scale, lb_dx, lb_dy = letterbox_image(frame, (net_w, net_h))
    img_rgb = cv2.cvtColor(letterboxed_img, cv2.COLOR_BGR2RGB)
    darknet.copy_image_from_bytes(darknet_image, img_rgb.tobytes())
    
    # Predict
    pnum = darknet.ct.pointer(darknet.ct.c_int(0))
    darknet.predict_image(net_yolo, darknet_image)
    dets = darknet.get_network_boxes(net_yolo, net_w, net_h, 0.10, 0.5, None, 0, pnum, 0)
    num = pnum[0]
    darknet.do_nms_sort(dets, num, 1, 0.4)
    
    # Parse bboxes
    yolo_boxes = []
    yolo_confs = []
    for j in range(num):
        prob = dets[j].prob[0]
        if prob > 0.10:
            bbox = dets[j].bbox
            cx_lb, cy_lb, w_lb, h_lb = bbox.x, bbox.y, bbox.w, bbox.h
            cx_orig = (cx_lb - lb_dx) / lb_scale
            cy_orig = (cy_lb - lb_dy) / lb_scale
            w_orig = w_lb / lb_scale
            h_orig = h_lb / lb_scale
            x_l = int(cx_orig - w_orig/2)
            y_t = int(cy_orig - h_orig/2)
            yolo_boxes.append([x_l, y_t, int(w_orig), int(h_orig)])
            yolo_confs.append(float(prob))
    darknet.free_detections(dets, num)
    times_yolo.append(time.time() - t0)
    
    # 4. Tracking
    t0 = time.time()
    dummy_dets = [{'box': b, 'conf': c} for b, c in zip(yolo_boxes, yolo_confs)]
    for d in dummy_dets:
        pass
    times_tracking.append(time.time() - t0)
    
    # 5. Localization
    t0 = time.time()
    for b in yolo_boxes:
        _ = 10.0 / max(b[2] / 640.0, 1e-3)
    times_loc.append(time.time() - t0)
    
    # 6. HUD Drawing and writing to disk
    t0 = time.time()
    for b in yolo_boxes:
        cv2.rectangle(frame, (b[0], b[1]), (b[0]+b[2], b[1]+b[3]), (0,255,0), 2)
    cv2.imwrite("/home/jiacdi/bordershield_ai/latest_detection.jpg", frame)
    times_hud.append(time.time() - t0)
    
    times_total.append(time.time() - t_start)
    if frame_idx % 10 == 0:
        print("Processed {}/100 frames... Current frame time: {:.1f}ms".format(frame_idx, times_total[-1]*1000))

# Clean up
cap.release()
darknet.free_image(darknet_image)

# Output summary
print("\n" + "="*50)
print("BENCHMARK RESULTS OVER 100 FRAMES")
print("="*50)
print("1. Camera Capture:   {:.2f} ms".format(np.mean(times_capture)*1000))
print("2. SSD Inference:     {:.2f} ms".format(np.mean(times_ssd)*1000))
print("3. YOLO Inference:    {:.2f} ms".format(np.mean(times_yolo)*1000))
print("4. Tracking:          {:.2f} ms".format(np.mean(times_tracking)*1000))
print("5. Localization:      {:.2f} ms".format(np.mean(times_loc)*1000))
print("6. HUD & Save Image:  {:.2f} ms".format(np.mean(times_hud)*1000))
print("-"*50)
print("Average Total Frame Time: {:.2f} ms ({:.2f} FPS)".format(np.mean(times_total)*1000, 1.0 / np.mean(times_total)))
print("="*50)

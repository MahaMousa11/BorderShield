import cv2
import numpy as np
import os
import glob

# Darknet paths
DRONE_CFG = "/home/jiacdi/darknet/cfg/yolov3-tiny-drone.cfg"
DRONE_WEIGHTS = "/home/jiacdi/darknet/backup/yolov3-tiny-drone_best.weights"
DRONE_NAMES = "/home/jiacdi/darknet/data/obj.names"

# Load labels
with open(DRONE_NAMES, "r") as f:
    classes = [x.strip() for x in f.readlines() if x.strip()]

# Load network
net = cv2.dnn.readNetFromDarknet(DRONE_CFG, DRONE_WEIGHTS)
layer_names = net.getLayerNames()
out_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

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

# Find valid images
valid_dir = "/home/jiacdi/darknet/data/images/valid"
img_paths = glob.glob(os.path.join(valid_dir, "*.*"))
img_paths = [p for p in img_paths if p.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

print("Found {} validation images. Running benchmarks on the first 5 images containing detections...".format(len(img_paths)))

count = 0
for path in img_paths:
    if count >= 5:
        break
        
    frame = cv2.imread(path)
    if frame is None:
        continue
        
    h, w = frame.shape[:2]
    
    # ----------------------------------------------------
    # PIPELINE 1: PREVIOUS IMPLEMENTATION (Direct Stretch, No Objectness multiplication)
    # ----------------------------------------------------
    blob_old = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob_old)
    outs_old = net.forward(out_layers)
    
    dets_old = []
    for out in outs_old:
        for detection in out:
            scores = detection[5:]
            if len(scores) == 0:
                continue
            class_id = int(scores.argmax())
            confidence = float(scores[class_id])  # Old parsing
            
            if confidence > 0.05:  # Low threshold to capture weak ones
                cx, cy, bw, bh = detection[0:4]
                x_left = int((cx - bw / 2.0) * w)
                y_top = int((cy - bh / 2.0) * h)
                width_p = int(bw * w)
                height_p = int(bh * h)
                dets_old.append((class_id, confidence, [x_left, y_top, width_p, height_p]))
                
    # ----------------------------------------------------
    # PIPELINE 2: NEW IMPLEMENTATION (Letterboxed + Objectness multiplication)
    # ----------------------------------------------------
    letterboxed, scale, dx, dy = letterbox_image(frame, (416, 416))
    blob_new = cv2.dnn.blobFromImage(letterboxed, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob_new)
    outs_new = net.forward(out_layers)
    
    dets_new = []
    for out in outs_new:
        for detection in out:
            scores = detection[5:]
            if len(scores) == 0:
                continue
            objectness = float(detection[4])
            class_id = int(scores.argmax())
            confidence = objectness * float(scores[class_id])  # Correct parsing
            
            if confidence > 0.05:
                cx_norm, cy_norm, bw_norm, bh_norm = detection[0:4]
                cx_lb = cx_norm * 416
                cy_lb = cy_norm * 416
                w_lb = bw_norm * 416
                h_lb = bh_norm * 416
                
                cx_orig = (cx_lb - dx) / scale
                cy_orig = (cy_lb - dy) / scale
                w_orig = w_lb / scale
                h_orig = h_lb / scale
                
                x_left = int(cx_orig - w_orig / 2.0)
                y_top = int(cy_orig - h_orig / 2.0)
                width_p = int(w_orig)
                height_p = int(h_orig)
                dets_new.append((class_id, confidence, [x_left, y_top, width_p, height_p]))

    # Filter by NMS to keep it clean
    def apply_nms(boxes, confidences, score_threshold=0.05, nms_threshold=0.4):
        if not boxes:
            return []
        indices = cv2.dnn.NMSBoxes(boxes, confidences, score_threshold, nms_threshold)
        if len(indices) > 0:
            if hasattr(indices, "flatten"):
                return indices.flatten().tolist()
            else:
                return [int(x) for x in indices]
        return []

    # Old NMS
    old_boxes = [d[2] for d in dets_old]
    old_confs = [d[1] for d in dets_old]
    old_nms_idx = apply_nms(old_boxes, old_confs)
    final_old = [dets_old[i] for i in old_nms_idx]

    # New NMS
    new_boxes = [d[2] for d in dets_new]
    new_confs = [d[1] for d in dets_new]
    new_nms_idx = apply_nms(new_boxes, new_confs)
    final_new = [dets_new[i] for i in new_nms_idx]
    
    if final_old or final_new:
        count += 1
        print("\n=== Benchmark Image {}: {} ===".format(count, os.path.basename(path)))
        print("  Image Dimensions: {}x{}".format(w, h))
        print("  - PREVIOUS Pipeline (Stretched, No Objectness multiplication):")
        if not final_old:
            print("      No Detections")
        for d in final_old:
            print("      -> Class ID: {}, Conf: {:.2f}%, Box: {}".format(d[0], d[1]*100, d[2]))
            
        print("  - NEW Pipeline (Letterboxed, Objectness multiplied):")
        if not final_new:
            print("      No Detections")
        for d in final_new:
            print("      -> Class ID: {}, Conf: {:.2f}%, Box: {}".format(d[0], d[1]*100, d[2]))

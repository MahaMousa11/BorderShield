import sys
import os
import time
import cv2
import numpy as np

# Darknet directories
DARKNET_PATH = "/home/jiacdi/darknet"
sys.path.append(DARKNET_PATH)

# Load models
DRONE_CFG = "/home/jiacdi/darknet/cfg/yolov3-tiny-drone.cfg"
DRONE_WEIGHTS = "/home/jiacdi/darknet/backup/yolov3-tiny-drone_best.weights"
DRONE_NAMES = "/home/jiacdi/darknet/data/obj.names"
DRONE_DATA = "/home/jiacdi/darknet/data/obj.data"

# Validation image
test_img_path = "/home/jiacdi/darknet/data/dog.jpg"

print("=========================================")
print("BENCHMARK: CPU vs. GPU (Darknet)")
print("=========================================")

# 1. OpenCV CPU Benchmark
print("Running OpenCV CPU Benchmark (10 iterations)...")
try:
    net_cpu = cv2.dnn.readNetFromDarknet(DRONE_CFG, DRONE_WEIGHTS)
    net_cpu.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
    net_cpu.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    layer_names = net_cpu.getLayerNames()
    out_layers = [layer_names[i[0] - 1] for i in net_cpu.getUnconnectedOutLayers()]
    
    img = cv2.imread(test_img_path)
    if img is None:
        img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        print("Using dummy random image because dog.jpg was not found.")
    
    # Warmup
    blob = cv2.dnn.blobFromImage(img, 1/255.0, (416, 416), swapRB=True, crop=False)
    net_cpu.setInput(blob)
    net_cpu.forward(out_layers)
    
    cpu_times = []
    for _ in range(10):
        t0 = time.time()
        blob = cv2.dnn.blobFromImage(img, 1/255.0, (416, 416), swapRB=True, crop=False)
        net_cpu.setInput(blob)
        net_cpu.forward(out_layers)
        cpu_times.append(time.time() - t0)
    mean_cpu = np.mean(cpu_times) * 1000.0
    print("  -> OpenCV CPU Average: {:.2f} ms ({:.2f} FPS)".format(mean_cpu, 1000.0 / mean_cpu))
except Exception as e:
    print("OpenCV CPU benchmark failed:", e)
    mean_cpu = None

# 2. Darknet GPU Benchmark
print("Running Darknet GPU Benchmark (10 iterations)...")
try:
    # Set directory context for darknet
    os.chdir(DARKNET_PATH)
    import darknet
    
    # Load network
    darknet_net, class_names, colors = darknet.load_network(
        DRONE_CFG,
        DRONE_DATA,
        DRONE_WEIGHTS,
        batch_size=1
    )
    
    # Check dimensions
    width = darknet.network_width(darknet_net)
    height = darknet.network_height(darknet_net)
    
    # Load image in darknet format
    darknet_image = darknet.make_image(width, height, 3)
    
    # Read with opencv, resize, and copy bytes
    img_cv = cv2.imread(test_img_path)
    if img_cv is None:
        img_cv = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (width, height), interpolation=cv2.INTER_LINEAR)
    
    img_data = img_resized.tobytes()
    darknet.copy_image_from_bytes(darknet_image, img_data)
    
    # Warmup
    darknet.predict_image(darknet_net, darknet_image)
    
    gpu_times = []
    for _ in range(10):
        t0 = time.time()
        darknet.predict_image(darknet_net, darknet_image)
        gpu_times.append(time.time() - t0)
    mean_gpu = np.mean(gpu_times) * 1000.0
    print("  -> Darknet GPU Average: {:.2f} ms ({:.2f} FPS)".format(mean_gpu, 1000.0 / mean_gpu))
    
    # Free memory
    darknet.free_image(darknet_image)
except Exception as e:
    print("Darknet GPU benchmark failed:", e)
    mean_gpu = None

print("=========================================")
print("SUMMARY & RECOMMENDATION:")
if mean_cpu and mean_gpu:
    speedup = mean_cpu / mean_gpu
    print("  Darknet GPU is {:.1f}x faster than OpenCV CPU!".format(speedup))
print("=========================================")

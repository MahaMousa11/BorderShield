import cv2
import numpy as np

print("=========================================")
print("OpenCV CUDA Diagnosis")
print("=========================================")
print("OpenCV Version:", cv2.__version__)

has_cuda = hasattr(cv2, 'cuda')
print("cv2.cuda module available:", has_cuda)
if has_cuda:
    try:
        device_count = cv2.cuda.getCudaEnabledDeviceCount()
        print("CUDA Enabled Device Count:", device_count)
    except Exception as e:
        print("Error checking device count:", e)

try:
    print("DNN_BACKEND_CUDA constant exists:", hasattr(cv2.dnn, 'DNN_BACKEND_CUDA'))
    print("DNN_TARGET_CUDA constant exists:", hasattr(cv2.dnn, 'DNN_TARGET_CUDA'))
except Exception as e:
    print("Error checking DNN constants:", e)

try:
    # Try loading yolov3-tiny
    net = cv2.dnn.readNetFromDarknet(
        "/home/jiacdi/darknet/cfg/yolov3-tiny-drone.cfg",
        "/home/jiacdi/darknet/backup/yolov3-tiny-drone_best.weights"
    )
    
    # Try setting CUDA backend and target
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    print("Set net preferable backend to DNN_BACKEND_CUDA: SUCCESS")
    print("Set net preferable target to DNN_TARGET_CUDA: SUCCESS")
    
    # Try a dummy inference to see if the CUDA execution graph allocates and compiles successfully
    dummy = np.random.randn(1, 3, 416, 416).astype(np.float32)
    net.setInput(dummy)
    out_layers = [net.getLayerNames()[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    net.forward(out_layers)
    print("Dummy forward pass on CUDA: SUCCESS")
except Exception as e:
    print("CUDA backend test: FAILED with error:", e)
print("=========================================")

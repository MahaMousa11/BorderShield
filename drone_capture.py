import cv2
import os
from datetime import datetime
import time

os.makedirs("drone_detection/dataset/images", exist_ok=True)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Drone image capture started")
print("Show drone images/videos in front of camera")
print("CTRL+C to stop")

count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = "drone_detection/dataset/images/drone_{}_{}.jpg".format(timestamp, count)

        cv2.imwrite(filename, frame)
        print("Saved:", filename)

        count += 1
        time.sleep(2)

except KeyboardInterrupt:
    print("Stopped")

cap.release()
print("Total images:", count)

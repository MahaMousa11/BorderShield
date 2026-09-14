import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Camera not opened")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

ret, frame = cap.read()

if ret:
    cv2.imwrite("snapshot.jpg", frame)
    print("Saved snapshot.jpg")
else:
    print("ERROR: Failed to capture frame")

cap.release()

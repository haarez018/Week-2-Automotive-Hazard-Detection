# /backend/detection_logic.py  
# FULL VERSION WITH CLEAN SHUTDOWN WHEN VIDEO ENDS

import cv2
from ultralytics import YOLO
import os
import asyncio
import websockets
from pathlib import Path
import json
import numpy as np

# --- CONFIGURATION ---
WS_URL = "ws://127.0.0.1:8000/ws/video"

ROOT_DIR = Path(__file__).resolve().parent.parent
VIDEO_PATH = str(ROOT_DIR / "test_drive.mp4")

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")
print("YOLO model loaded ✅")

MIN_CONFIDENCE = 0.5
HAZARD_TYPE_POTHOLE = "Pothole"
HAZARD_TYPE_RASH = "Rash Driving"
RASH_MOVEMENT_THRESHOLD = 50

OBJECT_TRACKER = {}

FRAME_SKIP_COUNT = 3
JPEG_QUALITY = 60
ENCODE_PARAM = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]

VEHICLE_CLASSES = [2, 3, 5, 7]


# ----------------------------------------------------
# ✅ RASH DRIVING DETECTION LOGIC
# ----------------------------------------------------
def check_for_rash_driving(current_detections):
    global OBJECT_TRACKER
    rash_alerts = []
    current_ids = set()

    for box in current_detections:
        x1, y1, x2, y2, track_id, cls = box

        if int(cls) not in VEHICLE_CLASSES:
            continue

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        current_ids.add(track_id)

        if track_id in OBJECT_TRACKER:
            last_x, last_y = OBJECT_TRACKER[track_id]
            movement = abs(center_x - last_x)

            if movement > RASH_MOVEMENT_THRESHOLD:
                rash_alerts.append({
                    "id": track_id,
                    "movement": int(movement)
                })

        OBJECT_TRACKER[track_id] = (center_x, center_y)

    # Remove old inactive tracks
    stale = [tid for tid in OBJECT_TRACKER if tid not in current_ids]
    for tid in stale:
        del OBJECT_TRACKER[tid]

    return rash_alerts


# ----------------------------------------------------
# ✅ MAIN FUNCTION
# ----------------------------------------------------
async def stream_video_and_detect():

    print("\nChecking video file...")
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ ERROR: Video file not found: {VIDEO_PATH}")
        return
        
    print("✅ Video file found.")

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("❌ ERROR: Could not open video file.")
        return

    print("✅ Video stream opened.")

    frame_count = 0

    try:
        async with websockets.connect(WS_URL, open_timeout=5) as websocket:
            print(f"✅ WS CLIENT connected to {WS_URL}")

            while True:
                ret, frame = cap.read()

                # ✅ STOP WHEN VIDEO FINISHES
                if not ret:
                    print("✅ Video finished. Closing WebSocket.")
                    await websocket.close()
                    break

                frame_count += 1

                # ✅ Skip frames to boost FPS
                if frame_count % FRAME_SKIP_COUNT != 0:
                    continue

                # YOLO tracking
                print("🔍 YOLO Processing...")
                results = model.track(frame, conf=MIN_CONFIDENCE, persist=True, verbose=False)
                print("✅ YOLO Done")

                current_detections = []
                pothole_detected = False

                if (results 
                    and results[0].boxes.data is not None
                    and results[0].boxes.id is not None):

                    data = results[0].boxes.data.cpu().numpy()
                    ids = results[0].boxes.id.cpu().numpy()

                    for box, track_id in zip(data, ids):
                        x1, y1, x2, y2 = box[:4]
                        cls = box[-1]

                        current_detections.append([x1, y1, x2, y2, track_id, cls])

                        if int(cls) == 0:
                            pothole_detected = True

                rash_alerts = check_for_rash_driving(current_detections)

                # Annotated frame
                annotated = results[0].plot()

                # JPEG encode
                success, buffer = cv2.imencode(".jpg", annotated, ENCODE_PARAM)
                if not success:
                    print("❌ JPEG encoding failed")
                    continue

                frame_bytes = buffer.tobytes()

                print(f"📤 Sending frame ({len(frame_bytes)} bytes)")
                await websocket.send(frame_bytes)

                # Send hazard JSON
                if pothole_detected:
                    hazard = {
                        "type": HAZARD_TYPE_POTHOLE,
                        "severity": 8,
                        "frame_id": frame_count
                    }
                    print("⚠️ Sending Pothole Hazard JSON")
                    await websocket.send(json.dumps(hazard))

                for alert in rash_alerts:
                    hazard = {
                        "type": HAZARD_TYPE_RASH,
                        "severity": int(alert["movement"] / 10),
                        "frame_id": frame_count,
                        "track_id": int(alert["id"])
                    }
                    print("⚠️ Sending Rash Driving JSON")
                    await websocket.send(json.dumps(hazard))

                await asyncio.sleep(0.03)

            print("✅ Video stream ended.")

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

    finally:
        cap.release()
        print("✅ Video capture released.")
        print("✅ Script exited cleanly.")


if __name__ == "__main__":
    asyncio.run(stream_video_and_detect())

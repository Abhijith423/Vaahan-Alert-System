import time
import threading
from datetime import datetime
import cv2
import requests
from ultralytics import YOLO

# --- CONFIGURATION ---
VIDEO_PATH = "road_sample.mp4"
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/vehicle-proximity-alert"
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

PROXIMITY_AREA_THRESHOLD = 0.08
GROWTH_RATE_THRESHOLD = 0.004
ALERT_COOLDOWN_SEC = 10

model = YOLO("yolo26n.pt")
cap = cv2.VideoCapture(VIDEO_PATH)

track_history = {}
alerted_tracks = {}


def send_to_n8n(payload: dict):
    try:
        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=3)
        print(f"[n8n SENT] {payload}")
    except Exception as e:
        print(f"[n8n ERROR] {e}")


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    frame_area = w * h

    # Center ego-lane zone
    lane_x_min, lane_x_max = int(w * 0.25), int(w * 0.75)
    cv2.rectangle(frame, (lane_x_min, int(h * 0.4)), (lane_x_max, h), (255, 255, 0), 1)

    results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        classes = results[0].boxes.cls.int().cpu().tolist()
        confs = results[0].boxes.conf.cpu().tolist()

        for box, tid, cls_id, conf in zip(boxes, track_ids, classes, confs):
            if cls_id not in VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box)
            cx = (x1 + x2) // 2
            box_area = (x2 - x1) * (y2 - y1)
            area_ratio = box_area / frame_area

            history = track_history.setdefault(tid, [])
            history.append(area_ratio)
            if len(history) > 6:
                history.pop(0)

            growth_rate = (history[-1] - history[0]) / len(history) if len(history) >= 3 else 0.0
            in_ego_lane = lane_x_min <= cx <= lane_x_max

            is_approaching = in_ego_lane and (
                area_ratio >= PROXIMITY_AREA_THRESHOLD or growth_rate >= GROWTH_RATE_THRESHOLD
            )

            color = (0, 0, 255) if is_approaching else (0, 255, 0)
            status = "APPROACHING!" if is_approaching else "Tracking"
            label = f"ID:{tid} {VEHICLE_CLASSES[cls_id]} [{status}]"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(y1 - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            if is_approaching:
                now = time.time()
                if now - alerted_tracks.get(tid, 0) > ALERT_COOLDOWN_SEC:
                    alerted_tracks[tid] = now
                    payload = {
                        "event": "VEHICLE_PROXIMITY_ALERT",
                        "track_id": tid,
                        "vehicle_type": VEHICLE_CLASSES[cls_id],
                        "confidence": round(conf, 2),
                        "area_ratio": round(area_ratio, 4),
                        "growth_rate": round(growth_rate, 5),
                        "timestamp": datetime.now().isoformat()
                    }
                    threading.Thread(target=send_to_n8n, args=(payload,), daemon=True).start()

    cv2.imshow("Vehicle Proximity & n8n MVP", frame)
    if cv2.waitKey(30) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
   # Vaahan-Alert-System

Real-time vehicle proximity detection,  Artificial Intelligence Automation, CSV incident logging, and live alert dashboard built with **Python (YOLO + ByteTrack + OpenCV)**, **n8n**, and **Next.js**.

## Overview

`Vaahan-Alert-System` monitors road video frames for approaching vehicles inside the center ego-lane zone, estimates bounding-box `area_ratio` and `growth_rate`, routes proximity events through an **n8n** workflow for risk classification (`MEDIUM` / `HIGH`) and CSV export, and streams live SMS-style alerts to a **Next.js** dashboard (`http://localhost:3000`).

## Architecture & Pipeline

1. **Vehicle Tracking & Proximity Detection (`tracker_mvp.py`)**
   - Uses **YOLO** and **ByteTrack** (`bytetrack.yaml`) via **OpenCV** to detect and persist vehicle track IDs (`track_id`, `vehicle_type`, `confidence`).
   - Evaluates the ego-lane region of interest (`area_ratio` and `growth_rate`) and sends JSON proximity payloads to an **n8n** webhook (`POST`).

2. **n8n Automation & CSV Export (`n8n workflows.json`)**
   - **Webhook Node**: Receives incoming vehicle proximity payloads from Python.
   - **Code (JavaScript) Node**: Computes `risk_level` (`MEDIUM` or `HIGH`) and normalizes fields without relying on restricted sandbox file modules.
   - **Convert to File (CSV) & Read/Write Files from Disk**: Converts incident records into CSV format and writes them to disk.
   - **HTTP Request Node**: Forwards alert payloads to the Next.js API endpoint (`POST http://localhost:3000/api/alerts`).

3. **Live Alert Dashboard (`alert-dashboard/`)**
   - **`src/app/api/alerts/route.js`**: Handles `POST` alert ingestion and `GET` alert retrieval.
   - **`src/app/page.js`**: Polls `/api/alerts` and renders incoming SMS-style approach alerts alongside **Total Alerts** and **High Risk** counters in real time.

## Project Structure

```text
Vaahan-Alert-System/
├── tracker_mvp.py              # YOLO + ByteTrack + OpenCV proximity tracker
├── n8n workflows.json          # Exported n8n workflow configuration
├── .gitignore                  # Ignores venv, node_modules, .next, weights, videos, and CSVs
├── README.md
└── alert-dashboard/            # Next.js live alert web app
    └── src/
        └── app/
            ├── page.js         # Live alert UI & counters
            └── api/
                └── alerts/
                    └── route.js # Alerts API endpoint

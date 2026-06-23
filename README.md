# health_pose

Camera-based strength **rep counter + form checker** — a local, single-user
proof-of-concept. Point a webcam at yourself side-on; the browser shows the
annotated feed, a big rep counter, and live form cues.

Tracks **squats** today. The architecture is built so the rest of Circuit A
(push-ups, glute bridges, inverted rows, dead bug, plank) drops in as extra
rule modules. Fills the gap a smartwatch can't: rep counts and form feedback.

> Tracks issue **health-d5f**.

## Stack

- **MediaPipe Pose** — off-the-shelf keypoints (no model training).
- **OpenCV** — webcam capture + drawing overlays only (never pose).
- Rep counting — a rule-based **joint-angle state machine** (not ML).
- Form checks — rule-based **geometry** per exercise (not ML).
- **FastAPI** serves an MJPEG video stream + a WebSocket of live state.
- Front end — vanilla HTML/JS.

The rep/form rules ([app/exercises/](app/exercises/), [app/geometry.py](app/geometry.py))
are kept pure and portable so a later browser-only build (MediaPipe JS, pose
in-browser, no server) can mirror them in JavaScript cheaply.

## Run

Requires Python 3.10–3.12 (MediaPipe wheels) and a webcam.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main          # serves on http://localhost:8077
```

Open <http://localhost:8077>. Stand **side-on** so your hip, knee and ankle are
all visible. Hit **Reset** to zero the counter.

Port **8077** is the default to avoid the common 8000 clash; change it with
`HP_PORT`. To use uvicorn's auto-reload during development:
`uvicorn app.main:app --reload --port 8077`.

### Config (env vars)

| Var            | Default     | Meaning                          |
| -------------- | ----------- | -------------------------------- |
| `HP_PORT`      | `8077`      | HTTP port                        |
| `HP_HOST`      | `127.0.0.1` | Bind address                     |
| `HP_CAM_INDEX` | `0`         | Which camera OpenCV opens        |
| `HP_WIDTH`     | `960`       | Capture width                    |
| `HP_HEIGHT`    | `540`       | Capture height                   |

> **Why not Docker?** The server owns the webcam via OpenCV/DirectShow, and a
> Linux container under Docker Desktop on Windows can't reach the host camera.
> Containerizing would need the camera moved into the browser (MediaPipe JS) —
> tracked as a possible later pivot, not done here.

## Tests

The rep-counting state machine has unit tests that need no camera or MediaPipe:

```powershell
pip install pytest
pytest
```

## How squats are scored

Side-on knee angle (hip–knee–ankle) drives a state machine with hysteresis:
drop below `KNEE_DOWN` (120°) to enter the descent, rise back above `KNEE_UP`
(160°) to bank a rep. Per rep it grades:

- **Depth** — deepest knee angle must reach `DEPTH_OK` (≤100°), else "squat deeper".
- **Torso lean** — forward lean beyond `LEAN_MAX` (45° from vertical) → "chest up".

Rules are conservative by design — they flag gross faults, not millimetres.
Thresholds live at the top of [app/exercises/squat.py](app/exercises/squat.py).

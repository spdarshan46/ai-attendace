# ==========================================
#  ATTENDANCE.PY — Standalone CLI Marker
#
#  DEMO FLOW (what judges/viva will see):
#    1. Camera opens — header "AI FACE ATTENDANCE SYSTEM"
#    2. Face detected — corner-bracket box appears
#    3. Name + confidence shown:  DARSHAN  (97.4%)
#    4. "Press ENTER to confirm attendance" prompt
#    5. Employee presses ENTER → DB write → voice speaks
#    6. Status banner: "LOGIN RECORDED" or "LOGOUT RECORDED"
#
#  Controls:
#    ENTER  — confirm attendance for detected face
#    Q      — quit
# ==========================================

import face_recognition
import cv2
import numpy as np
import time
from datetime import datetime
from collections import deque

from database import employees, attendance, write_log
from voice import greet_login, greet_logout, say_spoof, say_error

TOLERANCE      = 0.50
SPOOF_FRAMES   = 12
SPOOF_MIN_MOVE = 3.0
COOLDOWN_SECS  = 5


def mark_attendance():
    """
    Full attendance loop.
    Face is detected and identified continuously.
    Attendance is only WRITTEN when ENTER is pressed.
    """

    # ── Load known faces from DB ──────────────────────────────────────────────
    known_encodings, known_ids, known_names = [], [], []
    for emp in employees.find():
        known_encodings.append(np.array(emp["face_encoding"]))
        known_ids.append(emp["emp_id"])
        known_names.append(emp["emp_name"])

    if not known_encodings:
        print("⚠️  No registered employees. Please add employees first.")
        return

    cap          = cv2.VideoCapture(0)
    face_history = deque(maxlen=SPOOF_FRAMES)
    last_marked  = {}          # emp_id → epoch (cooldown)

    # State for confirm UI
    pending      = None        # {"emp_id", "emp_name", "confidence"} | None
    status_msg   = ""          # e.g. "✓ LOGIN RECORDED"
    status_color = (0,255,130)
    status_until = 0           # show status_msg until this epoch

    print("✅  Attendance system started")
    print("    ENTER = confirm  |  Q = quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        h, w    = display.shape[:2]

        # ── Header bar ────────────────────────────────────────────────────────
        cv2.rectangle(display, (0, 0), (w, 60), (5, 5, 18), cv2.FILLED)
        cv2.putText(display,
                    "AI FACE ATTENDANCE SYSTEM",
                    (20, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 255, 200), 2)
        cv2.putText(display,
                    datetime.now().strftime("%H:%M:%S"),
                    (w - 115, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 180, 255), 2)

        # ── Status banner (shown for 2s after marking) ────────────────────────
        if time.time() < status_until:
            cv2.rectangle(display, (0, h - 60), (w, h), (5, 5, 18), cv2.FILLED)
            cv2.putText(display, status_msg,
                        (20, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                        status_color, 2)

        # ── Face detection ────────────────────────────────────────────────────
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb)
        encs = face_recognition.face_encodings(rgb, locs)

        pending = None   # reset pending each frame; re-detect below

        for face_enc, (top, right, bottom, left) in zip(encs, locs):
            cx = (left + right) // 2
            cy = (top  + bottom) // 2
            face_history.append((cx, cy))

            # ── Anti-spoof ────────────────────────────────────────────────────
            spoof = False
            if len(face_history) == SPOOF_FRAMES:
                var = float(np.var([p[0] for p in face_history]) +
                            np.var([p[1] for p in face_history]))
                spoof = var < SPOOF_MIN_MOVE

            if spoof:
                _draw_corner_box(display, top, right, bottom, left, (0, 0, 220))
                _label_above(display, "⚠ SPOOF DETECTED", left, top, (0, 0, 220))
                cv2.putText(display, "Move your head slightly",
                            (left, bottom + 26),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2)
                continue

            # ── face_distance for confidence % ───────────────────────────────
            distances       = face_recognition.face_distance(known_encodings, face_enc)
            best_idx        = int(np.argmin(distances))
            best_dist       = distances[best_idx]
            confidence      = round((1.0 - best_dist) * 100, 1)

            if best_dist >= TOLERANCE:
                # Unknown face
                _draw_corner_box(display, top, right, bottom, left, (0, 60, 220))
                _label_above(display, "UNKNOWN", left, top, (0, 60, 220))
                continue

            emp_id   = known_ids[best_idx]
            emp_name = known_names[best_idx]

            # ── Cooldown ──────────────────────────────────────────────────────
            if time.time() - last_marked.get(emp_id, 0) < COOLDOWN_SECS:
                _draw_corner_box(display, top, right, bottom, left, (0, 180, 255))
                _label_above(display,
                             f"{emp_name}  [cooldown]", left, top, (0, 180, 255))
                continue

            # ── IDENTIFIED — show name, confidence, confirm prompt ────────────
            pending = {"emp_id": emp_id, "emp_name": emp_name, "confidence": confidence}

            _draw_corner_box(display, top, right, bottom, left, (0, 255, 130))

            # Name + confidence tag
            _label_above(display,
                         f"{emp_name.upper()}  ({confidence}%)",
                         left, top, (0, 255, 130))

            # Today's status hint
            today  = datetime.now().strftime("%Y-%m-%d")
            record = attendance.find_one({"emp_id": emp_id, "date": today})
            if not record:
                action_hint = "→ LOGIN"
                hint_color  = (0, 255, 130)
            elif not record.get("logout_time"):
                action_hint = "→ LOGOUT"
                hint_color  = (0, 200, 255)
            else:
                action_hint = "✓ COMPLETED"
                hint_color  = (120, 120, 120)

            # Confirm prompt bar below face
            cv2.rectangle(display,
                           (left, bottom + 5),
                           (right, bottom + 52),
                           (10, 10, 30), cv2.FILLED)
            cv2.putText(display,
                        f"Press ENTER to confirm  {action_hint}",
                        (left + 6, bottom + 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58,
                        hint_color, 2)

        # ── No face ───────────────────────────────────────────────────────────
        if not locs:
            pending = None
            cv2.putText(display,
                        "Align face with camera ...",
                        (w // 2 - 155, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                        (60, 60, 80), 2)

        cv2.imshow("AI Face Attendance  |  ENTER = confirm  |  Q = quit", display)

        # ── Key handling ──────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:    # Q or ESC → quit
            break

        if key == 13 and pending:           # ENTER → confirm attendance
            emp_id   = pending["emp_id"]
            emp_name = pending["emp_name"]
            conf     = pending["confidence"]

            today    = datetime.now().strftime("%Y-%m-%d")
            now_time = datetime.now().strftime("%H:%M:%S")
            record   = attendance.find_one({"emp_id": emp_id, "date": today})

            if not record:
                attendance.insert_one({
                    "emp_id":      emp_id,
                    "emp_name":    emp_name,
                    "date":        today,
                    "login_time":  now_time,
                    "logout_time": ""
                })
                write_log("Login",
                          f"{emp_name} IN at {now_time}  ({conf}%)", "SUCCESS")
                print(f"🟢  {emp_name:20s}  IN   {now_time}  ({conf}%)")
                status_msg   = f"✓  LOGIN RECORDED  —  {emp_name}  {now_time}"
                status_color = (0, 255, 130)
                greet_login(emp_name)

            elif not record.get("logout_time"):
                attendance.update_one(
                    {"emp_id": emp_id, "date": today},
                    {"$set": {"logout_time": now_time}}
                )
                write_log("Logout",
                          f"{emp_name} OUT at {now_time}  ({conf}%)", "INFO")
                print(f"🔴  {emp_name:20s}  OUT  {now_time}  ({conf}%)")
                status_msg   = f"✓  LOGOUT RECORDED  —  {emp_name}  {now_time}"
                status_color = (0, 200, 255)
                greet_logout(emp_name)

            else:
                status_msg   = f"ℹ  {emp_name} already completed today"
                status_color = (150, 150, 150)
                print(f"ℹ️   {emp_name} already completed today.")

            last_marked[emp_id] = time.time()
            status_until        = time.time() + 2.5
            pending             = None

    cap.release()
    cv2.destroyAllWindows()
    print("📷  Camera closed.")


# ── Visual helpers ────────────────────────────────────────────────────────────
def _draw_corner_box(img, top, right, bottom, left,
                      color=(0, 255, 130), thickness=2, corner=22):
    """AI-style corner-bracket bounding box."""
    for (x, y), (dx, dy) in [
        ((left,  top),    ( corner,  corner)),
        ((right, top),    (-corner,  corner)),
        ((left,  bottom), ( corner, -corner)),
        ((right, bottom), (-corner, -corner)),
    ]:
        cv2.line(img, (x, y), (x+dx, y),    color, thickness)
        cv2.line(img, (x, y), (x,    y+dy), color, thickness)


def _label_above(img, text, left, top, color=(0, 255, 130)):
    """Solid filled pill label above the bounding box."""
    label = f"  {text}  "
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.68, 2)
    y0 = max(top - 36, 0)
    cv2.rectangle(img, (left, y0), (left + tw, y0 + th + 10), color, cv2.FILLED)
    cv2.putText(img, label,
                (left, y0 + th + 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.68,
                (0, 0, 0), 2)


# ── Direct run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mark_attendance()
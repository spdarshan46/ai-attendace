import cv2
import face_recognition
import os

# ==========================================
#  REGISTER.PY — Face Capture & Encoding
# ==========================================
# Saves a reference photo to  faces/<emp_id>.jpg
# and returns the 128-D numpy encoding.

FACES_DIR = "faces"


def capture_face_encoding(emp_name: str, emp_id: str = None):
    """
    Opens webcam. Draws a live bounding box around any detected face.
    On first successful detection: saves a reference photo (if emp_id given)
    and returns the 128-D encoding vector.

    Returns:
        numpy array (128,) on success, or None if cancelled / no face.
    """
    os.makedirs(FACES_DIR, exist_ok=True)

    cap      = cv2.VideoCapture(0)
    encoding = None
    saved_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        h, w    = display.shape[:2]

        # Guide overlay — target rectangle
        cv2.rectangle(display,
                       (w // 4,     h // 4),
                       (3 * w // 4, 3 * h // 4),
                       (0, 255, 170), 1)

        # Header bar
        cv2.rectangle(display, (0, 0), (w, 50), (10, 10, 30), cv2.FILLED)
        cv2.putText(display,
                    f"REGISTERING: {emp_name.upper()}",
                    (10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 220, 255), 2)

        # Detect faces
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb)

        if locs:
            encs = face_recognition.face_encodings(rgb, locs)

            for (top, right, bottom, left), enc in zip(locs, encs):
                # Green bounding box with rounded corners (via lines)
                _draw_box(display, top, right, bottom, left,
                          color=(0, 255, 150), thickness=2)

                cv2.putText(display,
                            f"{emp_name}  [LOCKED]",
                            (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                            (0, 255, 150), 2)

                # Take the first face
                if encs:
                    encoding    = encs[0]
                    saved_frame = frame.copy()
                    break

        else:
            cv2.putText(display,
                        "Align face in box — stay still",
                        (10, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (100, 100, 255), 2)

        cv2.putText(display,
                    "ESC = Cancel",
                    (w - 130, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (100, 100, 100), 1)

        cv2.imshow("Face Registration", display)

        if encoding is not None:
            # Flash success for 1 second then close
            success = display.copy()
            cv2.rectangle(success, (0, 0), (w, h), (0, 255, 100), 4)
            cv2.putText(success, "✓ FACE CAPTURED",
                        (w // 2 - 110, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (0, 255, 100), 3)
            cv2.imshow("Face Registration", success)
            cv2.waitKey(900)
            break

        if cv2.waitKey(1) & 0xFF == 27:   # ESC
            encoding = None
            break

    cap.release()
    cv2.destroyAllWindows()

    # Save reference photo
    if encoding is not None and emp_id and saved_frame is not None:
        path = os.path.join(FACES_DIR, f"{emp_id}.jpg")
        cv2.imwrite(path, saved_frame)
        print(f"📸 Face photo saved → {path}")

    return encoding


# ── Helper: corner bracket style box ─────────────────────────────────────────
def _draw_box(img, top, right, bottom, left,
              color=(0, 255, 150), thickness=2, corner=20):
    """Draw a corner-bracket bounding box (looks more AI/pro than plain rect)."""
    tl = (left,  top)
    tr = (right, top)
    bl = (left,  bottom)
    br = (right, bottom)

    for pt, dx, dy in [
        (tl,  corner,  corner),
        (tr, -corner,  corner),
        (bl,  corner, -corner),
        (br, -corner, -corner),
    ]:
        x, y = pt
        cv2.line(img, pt, (x + dx, y),         color, thickness)
        cv2.line(img, pt, (x,      y + dy),     color, thickness)
# ==========================================
#  EMPLOYEE_PANEL.PY — Clock In / Out
#
#  GUI scan worker now uses confirm flow:
#    1. Face detected → show name (confidence%)
#    2. Show "Press ENTER to confirm" prompt
#    3. Only returns match after ENTER is pressed
#    4. Voice speaks welcome/goodbye message
# ==========================================

import customtkinter as ctk
import queue, threading, os
import numpy as np, face_recognition, cv2
from datetime import datetime
from tkinter import messagebox
from collections import deque

from ui.theme import *
from ui.components.widgets import FaceAnimCanvas, NeonButton
from database import employees, attendance, write_log
from voice import greet_login, greet_logout, say_error, say_already_in, say_already_out

TOLERANCE      = 0.5
SPOOF_FRAMES   = 12
SPOOF_MIN_MOVE = 3.0
FACES_DIR      = "faces"


class EmployeePanel(ctk.CTkFrame):

    def __init__(self, parent, on_back):
        super().__init__(parent, fg_color=BG_BASE, corner_radius=0)
        self.pack(fill="both", expand=True)
        self._on_back    = on_back
        self._scan_queue = None
        self._stop_event = None
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        bar = ctk.CTkFrame(self, height=60, fg_color=BG_SURFACE, corner_radius=0)
        bar.pack(fill="x")

        ctk.CTkLabel(bar, text="EMPLOYEE PORTAL",
                     font=("Courier New", 18, "bold"),
                     text_color=NEON_GREEN).pack(side="left", padx=PAD_LG, pady=PAD_MD)

        self._clock_lbl = ctk.CTkLabel(bar, text="",
                                        font=("Courier New", 13),
                                        text_color=NEON_BLUE)
        self._clock_lbl.pack(side="left", padx=PAD_LG)
        self._tick()

        NeonButton(bar, text="← Home",
                   accent=NEON_PINK, width=100, height=36,
                   command=self._on_back).pack(side="right", padx=PAD_LG)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD_XL, pady=PAD_LG)

        self._build_left(body)
        self._build_right(body)

    # ── Left: face animator + status pipeline ─────────────────────────────────
    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=RADIUS_LG)
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        ctk.CTkLabel(left, text="Face Authentication",
                     font=FONT_HEADING,
                     text_color=NEON_GREEN).pack(pady=(PAD_LG, PAD_SM))
        ctk.CTkLabel(left, text="Position your face in front of the camera",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY).pack()

        self._face_anim = FaceAnimCanvas(left, size=240, accent=NEON_GREEN)
        self._face_anim.pack(pady=PAD_LG)

        # Stage pipeline
        pipeline_frame = ctk.CTkFrame(left, fg_color=BG_ELEVATED,
                                       corner_radius=RADIUS_MD)
        pipeline_frame.pack(fill="x", padx=PAD_LG, pady=PAD_SM)

        self._stages = []
        for s in ["⬡ Ready", "◌ Scanning", "◈ Detected", "◉ Confirm", "✓ Done"]:
            lbl = ctk.CTkLabel(pipeline_frame, text=s,
                               font=("Courier New", 10), text_color=TEXT_MUTED)
            lbl.pack(side="left", expand=True, pady=PAD_SM)
            self._stages.append(lbl)

        self._status_lbl = ctk.CTkLabel(
            left, text="Ready to scan",
            font=("Courier New", 15, "bold"), text_color=NEON_BLUE)
        self._status_lbl.pack(pady=(PAD_MD, 0))

        self._substatus_lbl = ctk.CTkLabel(
            left, text="Press Login or Logout below",
            font=FONT_MICRO, text_color=TEXT_MUTED)
        self._substatus_lbl.pack(pady=(2, PAD_LG))

        self._set_stage(0)

    # ── Right: buttons + feed ─────────────────────────────────────────────────
    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        actions = ctk.CTkFrame(right, fg_color=BG_SURFACE, corner_radius=RADIUS_LG)
        actions.pack(fill="x")

        ctk.CTkLabel(actions, text="Quick Actions",
                     font=FONT_HEADING, text_color=NEON_BLUE).pack(pady=(PAD_LG, PAD_SM))

        self._login_btn = NeonButton(
            actions, text="🟢  LOGIN via Face",
            accent=NEON_GREEN, height=56, command=self._do_login)
        self._login_btn.pack(fill="x", padx=PAD_LG, pady=PAD_SM)

        self._logout_btn = NeonButton(
            actions, text="🔴  LOGOUT via Face",
            accent=NEON_PINK, height=56, command=self._do_logout)
        self._logout_btn.pack(fill="x", padx=PAD_LG, pady=PAD_SM)

        ctk.CTkFrame(actions, height=1,
                     fg_color=DIVIDER_COLOR).pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        ctk.CTkLabel(actions,
                     text="Camera opens → face detected → press ENTER to confirm",
                     font=FONT_MICRO, text_color=TEXT_MUTED,
                     wraplength=260).pack(pady=(0, PAD_MD))

        # Activity feed
        self._activity_card = ctk.CTkFrame(right, fg_color=BG_SURFACE,
                                            corner_radius=RADIUS_LG)
        self._activity_card.pack(fill="both", expand=True, pady=(PAD_MD, 0))

        ctk.CTkLabel(self._activity_card, text="Today's Activity",
                     font=FONT_SUBHEAD, text_color=NEON_BLUE).pack(
            anchor="w", padx=PAD_MD, pady=(PAD_MD, PAD_SM))

        self._feed = ctk.CTkScrollableFrame(
            self._activity_card, fg_color="transparent", height=200)
        self._feed.pack(fill="both", expand=True, padx=PAD_SM, pady=PAD_SM)
        self._refresh_feed()

    # ── Clock ─────────────────────────────────────────────────────────────────
    def _tick(self):
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._tick)

    # ── Stage controller ──────────────────────────────────────────────────────
    def _set_stage(self, active_idx, color=None):
        for i, lbl in enumerate(self._stages):
            if i < active_idx:
                lbl.configure(text_color=NEON_GREEN)
            elif i == active_idx:
                lbl.configure(text_color=color or NEON_YELLOW)
            else:
                lbl.configure(text_color=TEXT_MUTED_D)

    def _set_status(self, text, sub="", color=NEON_BLUE):
        self._status_lbl.configure(text=text, text_color=color)
        self._substatus_lbl.configure(text=sub)

    # ── Async face scan with CONFIRM flow ─────────────────────────────────────
    def _start_scan(self, callback):
        """
        Background camera thread:
          • Continuously shows face box + name (confidence%)
          • Waits for ENTER before returning the match
          • Updates GUI status stages via thread-safe after() calls
        """
        self._scan_queue = queue.Queue()
        self._stop_event = threading.Event()

        known_enc, known_ids, known_names = [], [], []
        for emp in employees.find():
            known_enc.append(np.array(emp["face_encoding"]))
            known_ids.append(emp["emp_id"])
            known_names.append(emp["emp_name"])

        stop_evt = self._stop_event
        result_q = self._scan_queue

        def worker():
            if not known_enc:
                result_q.put(None)
                return

            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            matched      = None
            face_history = deque(maxlen=SPOOF_FRAMES)

            while not stop_evt.is_set():
                ret, frame = cap.read()
                if not ret:
                    break

                display = frame.copy()
                h, w    = display.shape[:2]

                # ── Header bar ────────────────────────────────────────────────
                cv2.rectangle(display, (0, 0), (w, 60), (5, 5, 18), cv2.FILLED)
                cv2.putText(display, "AI FACE ATTENDANCE SYSTEM",
                            (20, 38), cv2.FONT_HERSHEY_SIMPLEX,
                            0.88, (0, 255, 200), 2)
                cv2.putText(display,
                            datetime.now().strftime("%H:%M:%S"),
                            (w - 115, 38), cv2.FONT_HERSHEY_SIMPLEX,
                            0.65, (0, 180, 255), 2)

                rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locs = face_recognition.face_locations(rgb)
                encs = face_recognition.face_encodings(rgb, locs)

                detected_this_frame = False

                for face_enc, (top, right, bottom, left) in zip(encs, locs):
                    cx = (left + right) // 2
                    cy = (top  + bottom) // 2
                    face_history.append((cx, cy))

                    # Spoof check
                    spoof = False
                    if len(face_history) == SPOOF_FRAMES:
                        var = float(np.var([p[0] for p in face_history]) +
                                    np.var([p[1] for p in face_history]))
                        spoof = var < SPOOF_MIN_MOVE

                    if spoof:
                        _draw_corner_box(display, top, right, bottom, left, (0, 0, 220))
                        _label_above(display, "SPOOF DETECTED", left, top, (0, 0, 220))
                        continue

                    # ── face_distance → confidence ────────────────────────────
                    dists    = face_recognition.face_distance(known_enc, face_enc)
                    best_idx = int(np.argmin(dists))
                    best_d   = dists[best_idx]
                    conf     = round((1.0 - best_d) * 100, 1)

                    if best_d >= TOLERANCE:
                        _draw_corner_box(display, top, right, bottom, left, (0, 60, 220))
                        _label_above(display, "UNKNOWN", left, top, (0, 60, 220))
                        continue

                    emp_id   = known_ids[best_idx]
                    emp_name = known_names[best_idx]
                    detected_this_frame = True

                    # Green box + name tag with confidence
                    _draw_corner_box(display, top, right, bottom, left, (0, 255, 130))
                    _label_above(display,
                                 f"{emp_name.upper()}  ({conf}%)",
                                 left, top, (0, 255, 130))

                    # Confirm prompt below face box
                    cv2.rectangle(display,
                                   (left, bottom + 5),
                                   (right, bottom + 55),
                                   (10, 10, 30), cv2.FILLED)
                    cv2.putText(display,
                                "Press ENTER to confirm",
                                (left + 6, bottom + 32),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.58,
                                (0, 255, 130), 2)

                    # ──not  Wait for ENTER ────────────────────────────────────────
                    cv2.imshow("AI Face Attendance", display)
                    matched = {
                        "emp_id":     emp_id,
                        "emp_name":   emp_name,
                        "confidence": conf}
                    stop_evt.set()
                    # Flash green success for 0.6s
                    _flash_success(display, emp_name, conf, h, w)
                    cv2.imshow("AI Face Attendance", display)
                    cv2.waitKey(600)
                    break

                if stop_evt.is_set():
                    break

                # No face / no match — show hint
                if not detected_this_frame and not locs:
                    cv2.putText(display,
                                "Align your face with the camera ...",
                                (w // 2 - 190, h // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.72,
                                (55, 55, 70), 2)

                cv2.imshow("AI Face Attendance", display)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            cap.release()
            cv2.destroyAllWindows()
            result_q.put(matched)

        threading.Thread(target=worker, daemon=True).start()
        self._poll_scan(callback)

    def _poll_scan(self, callback):
        try:
            result = self._scan_queue.get_nowait()
            callback(result)
        except queue.Empty:
            self._set_stage(2, NEON_YELLOW)
            self.after(150, lambda: self._poll_scan(callback))

    # ── Login ─────────────────────────────────────────────────────────────────
    def _do_login(self):
        self._login_btn.configure(state="disabled")
        self._logout_btn.configure(state="disabled")
        self._set_stage(1)
        self._set_status("Scanning…", "Look at the camera", NEON_YELLOW)

        def on_result(emp):
            self._login_btn.configure(state="normal")
            self._logout_btn.configure(state="normal")

            if not emp:
                self._set_stage(0)
                self._set_status("Not recognised", "Try again", NEON_PINK)
                self._face_anim.set_error()
                write_log("Login Attempt", "Face not recognised", "WARNING")
                say_error()
                messagebox.showerror("Error", "Face not recognised or cancelled.")
                return

            conf  = emp.get("confidence", 0)
            self._set_stage(3, NEON_BLUE)
            self._set_status(f"Confirmed: {emp['emp_name']}",
                             f"{conf}% confidence", NEON_BLUE)

            today = datetime.now().strftime("%Y-%m-%d")
            now   = datetime.now().strftime("%H:%M:%S")

            if attendance.find_one({"emp_id": emp["emp_id"], "date": today}):
                self._set_stage(0)
                self._set_status("Already logged in", "", NEON_ORANGE)
                say_already_in(emp["emp_name"])
                messagebox.showwarning("Already In", "Already logged in today.")
                return

            attendance.insert_one({
                "emp_id":      emp["emp_id"],
                "emp_name":    emp["emp_name"],
                "date":        today,
                "login_time":  now,
                "logout_time": "",
                "confidence":  conf
            })
            write_log("Login",
                      f"{emp['emp_name']} IN at {now}  ({conf}%)", "SUCCESS")
            self._set_stage(4, NEON_GREEN)
            self._face_anim.set_success()
            self._set_status(f"Welcome, {emp['emp_name']}!",
                             f"Logged in at {now}  ·  {conf}% match", NEON_GREEN)
            greet_login(emp["emp_name"])
            self._refresh_feed()
            messagebox.showinfo("Logged In",
                                f"Welcome {emp['emp_name']}!\n"
                                f"Login at {now}  ({conf}% confidence)")
            self.after(3000, lambda: [self._set_stage(0),
                                      self._face_anim.reset()])

        self._start_scan(on_result)

    # ── Logout ────────────────────────────────────────────────────────────────
    def _do_logout(self):
        self._login_btn.configure(state="disabled")
        self._logout_btn.configure(state="disabled")
        self._set_stage(1)
        self._set_status("Scanning…", "Look at the camera", NEON_YELLOW)

        def on_result(emp):
            self._login_btn.configure(state="normal")
            self._logout_btn.configure(state="normal")

            if not emp:
                self._set_stage(0)
                self._set_status("Not recognised", "Try again", NEON_PINK)
                self._face_anim.set_error()
                say_error()
                messagebox.showerror("Error", "Face not recognised or cancelled.")
                return

            conf  = emp.get("confidence", 0)
            today = datetime.now().strftime("%Y-%m-%d")
            now   = datetime.now().strftime("%H:%M:%S")
            rec   = attendance.find_one({"emp_id": emp["emp_id"], "date": today})

            if not rec:
                self._set_stage(0)
                self._set_status("No login found", "", NEON_ORANGE)
                messagebox.showwarning("No record", "No login record for today.")
                return
            if rec.get("logout_time"):
                self._set_stage(0)
                self._set_status("Already logged out", "", NEON_ORANGE)
                say_already_out(emp["emp_name"])
                messagebox.showwarning("Already Out", "Already logged out today.")
                return

            attendance.update_one(
                {"emp_id": emp["emp_id"], "date": today},
                {"$set": {"logout_time": now}}
            )
            write_log("Logout",
                      f"{emp['emp_name']} OUT at {now}  ({conf}%)", "INFO")
            self._set_stage(4, NEON_GREEN)
            self._face_anim.set_success()
            self._set_status(f"Goodbye, {emp['emp_name']}!",
                             f"Logged out at {now}  ·  {conf}% match", NEON_ORANGE)
            greet_logout(emp["emp_name"])
            self._refresh_feed()
            messagebox.showinfo("Logged Out",
                                f"Goodbye {emp['emp_name']}!\n"
                                f"Logout at {now}  ({conf}% confidence)")
            self.after(3000, lambda: [self._set_stage(0),
                                      self._face_anim.reset()])

        self._start_scan(on_result)

    # ── Activity feed ─────────────────────────────────────────────────────────
    def _refresh_feed(self):
        for w in self._feed.winfo_children():
            w.destroy()

        today   = datetime.now().strftime("%Y-%m-%d")
        records = list(
            attendance.find({"date": today}).sort("login_time", -1).limit(12)
        )

        if not records:
            ctk.CTkLabel(self._feed, text="No activity yet today",
                         font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=PAD_MD)
            return

        for rec in records:
            active    = not rec.get("logout_time")
            dot_color = NEON_GREEN if active else NEON_ORANGE
            conf_str  = f"  {rec['confidence']}%" if rec.get("confidence") else ""

            row = ctk.CTkFrame(self._feed, fg_color=BG_ELEVATED,
                               corner_radius=RADIUS_SM)
            row.pack(fill="x", pady=2, padx=PAD_SM)

            # Photo thumbnail
            photo_path = os.path.join(FACES_DIR, f"{rec['emp_id']}.jpg")
            if os.path.exists(photo_path):
                try:
                    from PIL import Image
                    img     = Image.open(photo_path).resize((30, 30))
                    ctk_img = ctk.CTkImage(img, size=(30, 30))
                    ctk.CTkLabel(row, image=ctk_img, text="").pack(
                        side="left", padx=(PAD_SM, 2), pady=4)
                except Exception:
                    pass

            ctk.CTkLabel(row, text="●",
                         text_color=dot_color, font=FONT_MICRO).pack(
                side="left", padx=PAD_SM)

            detail = f"{rec['emp_name']}  in {rec['login_time']}{conf_str}"
            detail += f"  →  out {rec['logout_time']}" if rec.get("logout_time") \
                      else "  (active)"

            ctk.CTkLabel(row, text=detail, font=FONT_MICRO,
                         text_color=TEXT_SECONDARY).pack(side="left", pady=PAD_XS)


# ── cv2 visual helpers ────────────────────────────────────────────────────────
def _draw_corner_box(img, top, right, bottom, left,
                      color=(0, 255, 130), thickness=2, corner=22):
    for (x, y), (dx, dy) in [
        ((left,  top),    ( corner,  corner)),
        ((right, top),    (-corner,  corner)),
        ((left,  bottom), ( corner, -corner)),
        ((right, bottom), (-corner, -corner)),
    ]:
        cv2.line(img, (x, y), (x+dx, y),    color, thickness)
        cv2.line(img, (x, y), (x,    y+dy), color, thickness)


def _label_above(img, text, left, top, color=(0, 255, 130)):
    label = f"  {text}  "
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.68, 2)
    y0 = max(top - 36, 0)
    cv2.rectangle(img, (left, y0), (left+tw, y0+th+10), color, cv2.FILLED)
    cv2.putText(img, label, (left, y0+th+3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 0, 0), 2)


def _flash_success(img, name, conf, h, w):
    """Overlay a full-frame success flash before closing camera."""
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 30, 15), cv2.FILLED)
    cv2.addWeighted(overlay, 0.45, img, 0.55, 0, img)
    cv2.putText(img,
                f"CONFIRMED: {name.upper()}",
                (w // 2 - 200, h // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                (0, 255, 130), 3)
    cv2.putText(img,
                f"Confidence: {conf}%",
                (w // 2 - 110, h // 2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                (0, 200, 255), 2)
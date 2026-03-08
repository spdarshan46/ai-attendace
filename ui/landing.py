# ==========================================
#  LANDING.PY — Dynamic Animated Landing
#  No +22/+33/+44 alpha hacks.
#  Canvas colors are plain hex strings.
# ==========================================

import customtkinter as ctk
import math
import random
from ui.theme import *


class LandingPage(ctk.CTkFrame):
    """
    Full-screen animated landing:
      • Particle-field canvas background
      • Glitching title text
      • Pulsing HUD rings (valid solid colors)
      • Role-select cards with hover border
    """

    def __init__(self, parent, on_admin, on_employee):
        super().__init__(parent, fg_color=BG_BASE, corner_radius=0)
        self.pack(fill="both", expand=True)

        self._on_admin    = on_admin
        self._on_employee = on_employee
        self._particles   = []
        self._tick_count  = 0
        self._glitch_chars = "▓░▒█▄▀■□◆◇"

        self._build_bg_canvas()
        self._build_overlay()
        self._spawn_particles(60)
        self._animate()

    # ── Particle canvas background ────────────────────────────────────────────
    def _build_bg_canvas(self):
        bg_str = BG_DEEP_D if ctk.get_appearance_mode() == "Dark" else BG_DEEP_L
        self._canvas = ctk.CTkCanvas(
            self, bg=bg_str, highlightthickness=0
        )
        self._canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _spawn_particles(self, n):
        self.update_idletasks()
        W = self.winfo_width()  or 1600
        H = self.winfo_height() or 900
        for _ in range(n):
            x     = random.uniform(0, W)
            y     = random.uniform(0, H)
            r     = random.uniform(1, 2.5)
            speed = random.uniform(0.3, 1.1)
            angle = random.uniform(0, 2 * math.pi)
            color = random.choice([NEON_BLUE, NEON_PURPLE, NEON_PINK, NEON_GREEN])
            oid   = self._canvas.create_oval(
                x-r, y-r, x+r, y+r, fill=color, outline=""
            )
            self._particles.append({
                "id": oid, "x": x, "y": y,
                "r": r, "speed": speed, "angle": angle
            })

    def _animate(self):
        self._tick_count += 1
        W = self.winfo_width()  or 1600
        H = self.winfo_height() or 900

        for p in self._particles:
            p["x"] += math.cos(p["angle"]) * p["speed"]
            p["y"] += math.sin(p["angle"]) * p["speed"]
            if p["x"] > W + 5: p["x"] = -5
            if p["x"] < -5:    p["x"] = W + 5
            if p["y"] > H + 5: p["y"] = -5
            if p["y"] < -5:    p["y"] = H + 5
            r = p["r"]
            self._canvas.coords(p["id"],
                p["x"]-r, p["y"]-r, p["x"]+r, p["y"]+r)

        if self._tick_count % 40 == 0 and hasattr(self, "_glitch_label"):
            self._do_glitch()

        self.after(30, self._animate)

    def _do_glitch(self):
        original = "FACE ATTENDANCE"
        glitched = "".join(
            " " if c == " "
            else (random.choice(self._glitch_chars) if random.random() < 0.15 else c)
            for c in original
        )
        self._glitch_label.configure(text=glitched)
        self.after(80, lambda: self._glitch_label.configure(text=original))

    # ── Overlay ───────────────────────────────────────────────────────────────
    def _build_overlay(self):
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # HUD ring canvas — plain hex bg, plain hex ring colors
        ring_bg = BG_DEEP_D if ctk.get_appearance_mode() == "Dark" else BG_DEEP_L
        ring_canvas = ctk.CTkCanvas(
            center, width=300, height=300,
            bg=ring_bg, highlightthickness=0
        )
        ring_canvas.pack()
        self._build_hud_rings(ring_canvas)

        # Title
        self._glitch_label = ctk.CTkLabel(
            center, text="FACE ATTENDANCE",
            font=("Courier New", 42, "bold"),
            text_color=NEON_BLUE
        )
        self._glitch_label.pack(pady=(0, PAD_XS))

        ctk.CTkLabel(
            center,
            text="ENTERPRISE  ·  INTELLIGENCE  ·  SECURITY",
            font=("Courier New", 12),
            text_color=TEXT_SECONDARY
        ).pack(pady=(0, PAD_LG))

        # Role cards
        cards_row = ctk.CTkFrame(center, fg_color="transparent")
        cards_row.pack()

        self._role_card(cards_row, "🛡️", "ADMIN",
                        "Full system control", NEON_PURPLE,
                        self._on_admin).pack(side="left", padx=PAD_MD)
        self._role_card(cards_row, "👤", "EMPLOYEE",
                        "Clock in / Clock out", NEON_GREEN,
                        self._on_employee).pack(side="left", padx=PAD_MD)

        ctk.CTkLabel(
            center,
            text="Powered by face_recognition · MongoDB · CustomTkinter",
            font=FONT_MICRO, text_color=TEXT_MUTED
        ).pack(pady=(PAD_LG, 0))

    def _build_hud_rings(self, canvas):
        """Spinning dashed rings — all solid hex colors."""
        cx, cy = 150, 150
        # Three rings with different solid dim colors (no alpha)
        ring_colors = [NEON_BLUE_DIM, NEON_PURPLE_DIM, NEON_BLUE_MID]
        ring_radii  = [125, 95, 65]
        self._rings = []

        for r, c in zip(ring_radii, ring_colors):
            oid = canvas.create_oval(
                cx-r, cy-r, cx+r, cy+r,
                outline=c, width=1, dash=(6, 5)
            )
            self._rings.append(oid)

        self._hud_canvas = canvas
        self._hud_angle  = 0
        self._spin_rings()

    def _spin_rings(self):
        self._hud_angle += 0.8
        try:
            for i, oid in enumerate(self._rings):
                off = int(self._hud_angle * (i + 1)) % 11
                self._hud_canvas.itemconfig(oid, dashoffset=off)
        except Exception:
            pass
        self.after(30, self._spin_rings)

    def _role_card(self, parent, icon, title, subtitle, accent, cmd):
        card = ctk.CTkFrame(parent,
                             width=200, height=210,
                             fg_color=BG_SURFACE,
                             corner_radius=RADIUS_LG)
        card.pack_propagate(False)

        # Accent top strip
        ctk.CTkFrame(card, height=4, fg_color=accent,
                      corner_radius=2).pack(fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(inner, text=icon,
                     font=("Segoe UI", 40)).pack(pady=(PAD_SM, 0))
        ctk.CTkLabel(inner, text=title,
                     font=("Courier New", 18, "bold"),
                     text_color=accent).pack()
        ctk.CTkLabel(inner, text=subtitle,
                     font=FONT_MICRO,
                     text_color=TEXT_SECONDARY).pack(pady=(2, PAD_SM))

        from ui.components.widgets import NeonButton
        NeonButton(inner, text="ENTER →",
                   accent=accent, height=34, command=cmd).pack(fill="x")

        # Hover: solid border, no alpha
        def _on_enter(e):
            card.configure(border_width=1, border_color=accent)
        def _on_leave(e):
            card.configure(border_width=0)
        card.bind("<Enter>", _on_enter)
        card.bind("<Leave>", _on_leave)

        return card
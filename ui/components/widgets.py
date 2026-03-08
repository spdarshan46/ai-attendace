# ==========================================
#  WIDGETS.PY — Reusable UI Components
#  No +22/+33/+44 alpha hacks.
#  All fg_color uses (light, dark) tuples.
# ==========================================

import customtkinter as ctk
from ui.theme import *
import math


# ─── Glowing Stat Card ────────────────────────────────────────────────────────
class StatCard(ctk.CTkFrame):
    """Neon-accent stat card with top colour strip and hover border."""

    def __init__(self, parent, title, value, icon="📊",
                 accent=NEON_BLUE, trend=None, **kwargs):
        super().__init__(parent, fg_color=BG_SURFACE,
                         corner_radius=RADIUS_LG, **kwargs)

        # Accent top strip
        ctk.CTkFrame(self, height=4, fg_color=accent,
                      corner_radius=2).pack(fill="x")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        # Icon + label
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(top_row, text=icon, font=("Segoe UI", 26)).pack(side="left")
        ctk.CTkLabel(top_row, text=title, font=FONT_SMALL,
                     text_color=TEXT_SECONDARY,
                     wraplength=160).pack(side="right", anchor="ne")

        # Value
        self.value_label = ctk.CTkLabel(
            inner, text=str(value),
            font=("Segoe UI", 34, "bold"),
            text_color=accent
        )
        self.value_label.pack(anchor="w", pady=(PAD_SM, 0))

        # Trend indicator
        if trend:
            sym, pct, note = trend
            t_color = NEON_GREEN if sym == "↑" else NEON_PINK
            ctk.CTkLabel(inner, text=f"{sym} {pct}  {note}",
                         font=FONT_MICRO,
                         text_color=t_color).pack(anchor="w")

        # Hover glow (border outline, no alpha needed)
        self.bind("<Enter>", lambda e: self.configure(
            border_width=1, border_color=accent))
        self.bind("<Leave>", lambda e: self.configure(border_width=0))

    def update_value(self, value):
        self.value_label.configure(text=str(value))


# ─── Neon Button ──────────────────────────────────────────────────────────────
class NeonButton(ctk.CTkButton):
    """Pill-shaped neon button with darkened hover — no alpha."""

    def __init__(self, parent, text, accent=NEON_BLUE, **kwargs):
        super().__init__(
            parent,
            text=text,
            fg_color=accent,
            hover_color=_darken(accent),
            corner_radius=RADIUS_PILL,
            font=FONT_SUBHEAD,
            text_color=BG_DEEP_D,      # always dark text on bright button
            **kwargs
        )


# ─── Badge / Status Pill ──────────────────────────────────────────────────────
class Badge(ctk.CTkLabel):
    """
    Solid-colour pill badge.
    Uses accent as background, dark text — no alpha hack.
    """
    def __init__(self, parent, text, color=NEON_GREEN, **kwargs):
        super().__init__(
            parent,
            text=f"  {text}  ",
            fg_color=color,            # solid — valid in all modes
            text_color=BG_DEEP_D,      # dark text on bright bg
            corner_radius=RADIUS_PILL,
            font=FONT_MICRO,
            **kwargs
        )


# ─── Section Header ───────────────────────────────────────────────────────────
class SectionHeader(ctk.CTkFrame):
    def __init__(self, parent, title, subtitle=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=title, font=FONT_TITLE,
                     text_color=TEXT_PRIMARY).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=FONT_BODY,
                         text_color=TEXT_SECONDARY).pack(anchor="w")
        ctk.CTkFrame(self, height=2, fg_color=NEON_BLUE,
                     corner_radius=2).pack(fill="x", pady=(PAD_SM, 0))


# ─── Animated Face Scan Canvas ────────────────────────────────────────────────
class FaceAnimCanvas(ctk.CTkCanvas):
    """
    Pulsing HUD face scan animation.
    set_success() / set_error() / reset() to change state.
    Note: Canvas uses single hex strings (no tuples).
    """

    def __init__(self, parent, size=220, accent=NEON_BLUE, **kwargs):
        # Canvas bg must be a plain string — read current mode
        bg_str = _canvas_bg()
        super().__init__(
            parent, width=size, height=size,
            bg=bg_str, highlightthickness=0, **kwargs
        )
        self._s      = size
        self._acc    = accent
        self._scan_y = size // 3
        self._dir    = 1
        self._pulse  = 0
        self._state  = "scanning"
        self._draw_base()
        self._animate()

    def _draw_base(self):
        s = self._s
        c = self._acc
        cx = cy = s // 2
        r  = s // 3

        self.create_oval(cx-r, cy-r, cx+r, cy+r,
                          outline=c, width=2, tags="ring")

        br, bk = r - 4, 18
        for sx, sy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
            bx, by = cx + sx*br, cy + sy*br
            self.create_line(bx, by, bx + sx*bk, by,
                              fill=c, width=3, tags="bkt")
            self.create_line(bx, by, bx, by + sy*bk,
                              fill=c, width=3, tags="bkt")

        self.create_oval(cx-30, cy-16, cx-14, cy-4,
                          outline=c, width=2, tags="eye")
        self.create_oval(cx+14, cy-16, cx+30, cy-4,
                          outline=c, width=2, tags="eye")
        self.create_arc(cx-20, cy+6, cx+20, cy+24,
                         start=0, extent=-180,
                         outline=c, width=2, style="arc", tags="mouth")
        self.create_line(cx-r+8, self._scan_y,
                          cx+r-8, self._scan_y,
                          fill=c, width=2, tags="scan")

    def _animate(self):
        if self._state != "scanning":
            return
        s  = self._s
        cx = cy = s // 2
        r  = s // 3

        self._scan_y += self._dir * 3
        if   self._scan_y >= cy + r - 14: self._dir = -1
        elif self._scan_y <= cy - r + 14: self._dir =  1
        self.coords("scan", cx-r+8, self._scan_y, cx+r-8, self._scan_y)

        self._pulse = (self._pulse + 1) % 24
        self.itemconfig("ring", width=2 if self._pulse < 12 else 3)
        self.after(28, self._animate)

    def set_success(self):
        self._state = "success"
        for tag in ("ring", "eye", "mouth"):
            self.itemconfig(tag, outline=NEON_GREEN)
        self.itemconfig("ring",  width=4)
        self.itemconfig("scan",  fill=NEON_GREEN)
        self.itemconfig("bkt",   fill=NEON_GREEN)

    def set_error(self):
        self._state = "error"
        for tag in ("ring", "eye", "mouth"):
            self.itemconfig(tag, outline=NEON_PINK)
        self.itemconfig("ring",  width=4)
        self.itemconfig("scan",  fill=NEON_PINK)
        self.itemconfig("bkt",   fill=NEON_PINK)

    def reset(self):
        self._state  = "scanning"
        self._scan_y = self._s // 3
        self._dir    = 1
        c = self._acc
        for tag in ("ring", "eye", "mouth"):
            self.itemconfig(tag, outline=c)
        self.itemconfig("ring",  width=2)
        self.itemconfig("scan",  fill=c)
        self.itemconfig("bkt",   fill=c)
        self._animate()


# ─── Loading Spinner ──────────────────────────────────────────────────────────
class Spinner(ctk.CTkCanvas):
    def __init__(self, parent, size=40, color=NEON_BLUE, **kwargs):
        super().__init__(parent, width=size, height=size,
                          bg=_canvas_bg(), highlightthickness=0, **kwargs)
        self._size    = size
        self._color   = color
        self._angle   = 0
        self._running = True
        self._draw()

    def _draw(self):
        if not self._running:
            return
        s = self._size
        self.delete("all")
        self.create_arc(4, 4, s-4, s-4,
                         start=self._angle, extent=270,
                         outline=self._color, width=3, style="arc")
        self._angle = (self._angle + 8) % 360
        self.after(30, self._draw)

    def stop(self):
        self._running = False


# ── Helpers ───────────────────────────────────────────────────────────────────
def _darken(hex_color: str, factor: float = 0.72) -> str:
    """Return a darkened solid hex color — no alpha."""
    h    = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


def _canvas_bg() -> str:
    """Return a plain string background for tk.Canvas based on current mode."""
    import customtkinter as ctk
    return BG_SURFACE_D if ctk.get_appearance_mode() == "Dark" else BG_SURFACE_L
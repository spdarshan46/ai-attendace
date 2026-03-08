# ==========================================
#  THEME.PY — Design Tokens & Color System
#  NO alpha hacks. All colors are valid hex.
#  CustomTkinter supports fg_color=(light, dark)
#  tuples — used throughout for light mode.
# ==========================================

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Pure neon palette (dark mode) ─────────────────────────────────────────────
NEON_BLUE   = "#00d4ff"
NEON_PURPLE = "#7b2fff"
NEON_PINK   = "#ff2d78"
NEON_GREEN  = "#00ffaa"
NEON_ORANGE = "#ff6b2b"
NEON_YELLOW = "#ffe600"

# ── Solid tinted variants (replaces +22/+33/+44 alpha hacks) ─────────────────
#    These are pre-mixed with the dark background so they look like
#    semi-transparent neon — but are valid solid hex colors.
NEON_BLUE_DIM    = "#0a3a4a"   # replaces NEON_BLUE   + "22"
NEON_BLUE_MID    = "#0d4f66"   # replaces NEON_BLUE   + "33"
NEON_BLUE_BOLD   = "#0e6080"   # replaces NEON_BLUE   + "44"
NEON_PURPLE_DIM  = "#1e0a44"
NEON_PURPLE_MID  = "#2d1266"
NEON_PINK_DIM    = "#3d0a1e"
NEON_PINK_MID    = "#5c1030"   # replaces DANGER      + "33"  (hover)
NEON_GREEN_DIM   = "#003322"
NEON_GREEN_MID   = "#004d33"
NEON_ORANGE_DIM  = "#3d1a08"
NEON_YELLOW_DIM  = "#3d3300"

# ── Semantic aliases ──────────────────────────────────────────────────────────
SUCCESS = NEON_GREEN
WARNING = NEON_YELLOW
DANGER  = NEON_PINK
INFO    = NEON_BLUE

# ── Divider / separator color ─────────────────────────────────────────────────
DIVIDER_COLOR = "#1e2a33"       # replaces NEON_BLUE + "33" on separators

# ──────────────────────────────────────────────────────────────────────────────
#  DUAL-MODE BACKGROUND TOKENS
#  Format: (light_value, dark_value)
#  CustomTkinter uses them automatically based on appearance mode.
# ──────────────────────────────────────────────────────────────────────────────
BG_DEEP     = ("#e8eaf0", "#05050f")
BG_BASE     = ("#f0f2f7", "#0a0a1a")
BG_SURFACE  = ("#ffffff", "#10101f")
BG_ELEVATED = ("#e4e8f0", "#16162a")
BG_HOVER    = ("#dce0ec", "#1e1e35")
SIDEBAR_BG  = ("#d8dce8", "#0c0c1e")
SIDEBAR_HOVER = ("#c8ccdc", "#1a1a30")
HEADER_BG   = ("#e0e4f0", "#080818")

# ── For widgets that only accept a single string (Canvas, ttk) ───────────────
#    Use the _D (dark) or _L (light) suffix variants directly.
BG_DEEP_D    = "#05050f"
BG_BASE_D    = "#0a0a1a"
BG_SURFACE_D = "#10101f"
BG_ELEVATED_D= "#16162a"

BG_DEEP_L    = "#e8eaf0"
BG_BASE_L    = "#f0f2f7"
BG_SURFACE_L = "#ffffff"
BG_ELEVATED_L= "#e4e8f0"

# ── Text ──────────────────────────────────────────────────────────────────────
TEXT_PRIMARY   = ("#111122", "#ffffff")
TEXT_SECONDARY = ("#4a4a6a", "#8888aa")
TEXT_MUTED     = ("#8888aa", "#44445a")

# Single-value versions for widgets that don't accept tuples
TEXT_PRIMARY_D   = "#ffffff"
TEXT_SECONDARY_D = "#8888aa"
TEXT_MUTED_D     = "#44445a"
TEXT_PRIMARY_L   = "#111122"
TEXT_SECONDARY_L = "#4a4a6a"

# ── Typography ────────────────────────────────────────────────────────────────
FONT_DISPLAY = ("Segoe UI", 48, "bold")
FONT_TITLE   = ("Segoe UI", 28, "bold")
FONT_HEADING = ("Segoe UI", 20, "bold")
FONT_SUBHEAD = ("Segoe UI", 16, "bold")
FONT_BODY    = ("Segoe UI", 14)
FONT_SMALL   = ("Segoe UI", 12)
FONT_MICRO   = ("Segoe UI", 10)

# ── Radii ─────────────────────────────────────────────────────────────────────
RADIUS_SM  = 8
RADIUS_MD  = 15
RADIUS_LG  = 22
RADIUS_XL  = 30
RADIUS_PILL= 50

# ── Spacing ───────────────────────────────────────────────────────────────────
PAD_XS = 5
PAD_SM = 10
PAD_MD = 20
PAD_LG = 30
PAD_XL = 50


# ── ttk Treeview style ────────────────────────────────────────────────────────
def apply_tree_style():
    """Apply Cyber treeview style. Call before every Treeview creation."""
    from tkinter import ttk
    mode = ctk.get_appearance_mode()   # "Dark" or "Light"

    bg  = BG_SURFACE_D  if mode == "Dark" else BG_SURFACE_L
    hbg = BG_ELEVATED_D if mode == "Dark" else BG_ELEVATED_L
    fg  = TEXT_PRIMARY_D if mode == "Dark" else TEXT_PRIMARY_L
    sel = NEON_BLUE_MID  if mode == "Dark" else "#cce8f4"

    style = ttk.Style()
    style.theme_use("default")
    style.configure("Cyber.Treeview",
        background=bg,
        foreground=fg,
        fieldbackground=bg,
        rowheight=36,
        borderwidth=0,
    )
    style.configure("Cyber.Treeview.Heading",
        background=hbg,
        foreground=NEON_BLUE,
        font=("Segoe UI", 12, "bold"),
        relief="flat",
    )
    style.map("Cyber.Treeview",
        background=[("selected", sel)],
        foreground=[("selected", NEON_BLUE)],
    )


# ── Theme switcher (call from Settings) ──────────────────────────────────────
def set_theme(mode: str):
    """mode: 'Dark' | 'Light' | 'System'"""
    ctk.set_appearance_mode(
        mode.lower() if mode != "System" else "system"
    )
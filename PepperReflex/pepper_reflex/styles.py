from __future__ import annotations

# --- Core Color Palette (Deep Slate & Neon) ---
BACKGROUND = "#1a1b1e"      # Dark gray/black background
SURFACE = "#25262b"         # Dark gray for cards and input areas
SECTION_HEADER = "#2c2e33"  # Header panels
SECTION_BORDER = "#373a40"  # Subtle borders
ACCENT_BLUE = "#4dabf7"     # Action color
ACCENT_TEAL = "#63e6be"     # Active state color
ACCENT_FAULT = "#fa5252"    # Error states

TEXT_PRIMARY = "#e9ecef"    # Primary text
TEXT_MUTED = "#adb5bd"      # Secondary text

# --- Message Bubble Palette ---
USER_BUBBLE = "#373a40"
ASSISTANT_BUBBLE = "#2b3a4d"
MCP_BUBBLE = "#1f2329"
MCP_BORDER_COLOR = "#000000"

# --- Typography ---
FONT_SANS = "Inter, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', monospace"

# --- Shared UI Component Styles ---

# Navbar (Main Toolbar)
NAVBAR_STYLE = {
    "padding": "6px 10px",
    "border_bottom": f"1px solid {SECTION_BORDER}",
    "background_color": SECTION_HEADER,
    "color": TEXT_PRIMARY,
    "width": "100%",
    "align": "center",
}

# Toggle Buttons (Top Right)
TOGGLE_RADIUS = "2px"
TOGGLE_COMMON = {
    "font_size": "0.85em",
    "font_weight": "600",
    "padding": "4px 12px",
    "transition": "all 0.2s ease",
}

TOGGLE_ON_BG = ACCENT_TEAL
TOGGLE_ON_TEXT = BACKGROUND
TOGGLE_ON_BORDER = f"1px solid {ACCENT_TEAL}"

TOGGLE_OFF_BG = "transparent"
TOGGLE_OFF_TEXT = TEXT_PRIMARY
TOGGLE_OFF_BORDER = f"1px solid {SECTION_BORDER}"

# Column Headers (Settings, Chat, Cards)
COLUMN_HEADER_STYLE = {
    "padding": "6px 10px",
    "background_color": SECTION_HEADER,
    "border_bottom": f"1px solid {SECTION_BORDER}",
    "color": TEXT_PRIMARY,
    "font_weight": "bold",
    "font_family": FONT_SANS,
    "width": "100%",
}

# Settings Accordion
SETTINGS_PANEL_STYLE = {
    "border": f"1px solid {SECTION_BORDER}",
    "border_radius": "8px",
    "margin": "8px",
    "background_color": SURFACE,
}

ACCORDION_ROOT_STYLE = {
    "width": "100%",
}

ACCORDION_ITEM_STYLE = {
    "border": f"1px solid {SECTION_BORDER}",
    "background_color": SURFACE,
    "margin_bottom": "8px",
    "border_radius": "8px",
    "overflow": "hidden",
    "width": "100%",
}

ACCORDION_TRIGGER_STYLE = {
    "padding": "10px",
    "background_color": SECTION_HEADER,
    "color": TEXT_PRIMARY,
    "font_weight": "bold",
    "text_align": "left",
    "_hover": {"background_color": "#373a40"},
}

# Chat Input Area (The 90/10 Split)
CHAT_SCROLL_STYLE = {
    "flex": "1",
    "width": "100%",
    "overflow": "hidden",
}

CHAT_INPUT_ROW = {
    "padding": "8px",
    "background_color": SURFACE,
    "border_top": f"1px solid {SECTION_BORDER}",
    "width": "100%",
    "align": "center",
    "spacing": "2",
    "margin_top": "auto",
}

CHAT_TEXTAREA_STYLE = {
    "width": "90%",
    "height": "70px",
    "background_color": SURFACE,
    "color": TEXT_PRIMARY,
    "border": f"1px solid {SECTION_BORDER}",
    "focus_border_color": ACCENT_BLUE,
    "font_family": FONT_SANS,
    "padding": "10px",
}

SEND_BUTTON_STYLE = {
    "width": "10%",
    "height": "70px",
    "background_color": ACCENT_BLUE,
    "color": BACKGROUND,
    "font_weight": "bold",
    "border_radius": "2px",
}

# High-Fidelity Cards
COLUMN_CONTAINER = {
    "height": "100%",
    "width": "100%",
    "overflow_y": "auto",
    "align_items": "stretch",
}

CARDS_CONTAINER_STYLE = {
    "background_color": BACKGROUND,
}

CARD_STYLE = {
    "width": "100%",
    "height": "240px",
    "padding": "20px",
    "background_color": SURFACE,
    "border": f"1px solid {SECTION_BORDER}",
    "border_radius": "8px",
}
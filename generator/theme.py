"""Shared design tokens for every generated SVG.

Both factions appear in BOTH modes. "light" and "dark" only change the sky,
paper and text contrast so the art reads well on GitHub's light and dark themes.
"""

# Straw Hat side: Gear 5 Luffy (Nika) + Zoro
STRAW_HAT = {
    "nika_white": "#FFFDF7",
    "cream": "#FFF4DC",
    "sun_gold": "#F6B800",
    "sun_glow": "#FFD95A",
    "straw": "#E9C46A",
    "straw_band": "#C1121F",
    "luffy_red": "#D62828",
    "zoro_green": "#2E8B57",
    "zoro_light": "#5FD08A",
    "haki_black": "#1B1B1F",
    "sea": "#2A9DF4",
    "sea_deep": "#0E4C92",
}

# Akatsuki side: Itachi + Pain
AKATSUKI = {
    "cloak": "#0B0B10",
    "cloak_soft": "#1A1A24",
    "cloud_red": "#C1121F",
    "cloud_edge": "#FFFFFF",
    "sharingan": "#E5383B",
    "tomoe": "#0B0B10",
    "rinnegan": "#8E7CC3",
    "rinnegan_light": "#C9BCF0",
    "rain": "#3A506B",
    "crow": "#14141A",
}

# Per-mode surface tokens (GitHub light bg is #ffffff, dark bg is #0d1117)
MODES = {
    "light": {
        "page": "#FFFFFF",
        "sky_left": "#FFF4DC",   # Nika dawn
        "sky_right": "#EDE7F6",  # Amegakure overcast
        "panel": "#FFFDF7",
        "panel_edge": "#E6DCC6",
        "text": "#1B1B1F",
        "text_muted": "#5C5C66",
        "clash": "#F6B800",
    },
    "dark": {
        "page": "#0D1117",
        "sky_left": "#1F1608",   # golden night glow
        "sky_right": "#0B0B10",  # red-moon night
        "panel": "#11141B",
        "panel_edge": "#2A2F3A",
        "text": "#F5F1E8",
        "text_muted": "#A3A3B2",
        "clash": "#FFD95A",
    },
}

# Contribution level ramps (index 0 = no contributions, 4 = max quartile)
LEVELS = {
    "straw_hat": {
        "light": ["#EFE6D2", "#FFE08A", "#F6B800", "#5FD08A", "#2E8B57"],
        "dark": ["#1E1A12", "#6B5214", "#F6B800", "#3BB273", "#5FD08A"],
    },
    "akatsuki": {
        "light": ["#E9E4F2", "#C9BCF0", "#8E7CC3", "#E5383B", "#C1121F"],
        "dark": ["#16141E", "#3B2F63", "#8E7CC3", "#C1121F", "#FF4D5A"],
    },
}

# One "power level" ramp for contribution intensity, indexed by GitHub's own
# contribution level (0 = none, 4 = top quartile): gold for light days, crimson
# for the hottest. Colour always means intensity, never which side of the theme.
POWER = {
    "light": ["#EFE6D2", "#FFE08A", "#F6B800", "#E5383B", "#C1121F"],
    "dark": ["#1E1A12", "#6B5214", "#F6B800", "#E5383B", "#FF4D5A"],
}

# System fonts only: SVGs served through <img> cannot load web fonts.
FONT_DISPLAY = "'Impact','Haettenschweiler','Arial Narrow Bold','Arial Black',sans-serif"
FONT_SERIF = "'Georgia','Times New Roman',serif"
FONT_BODY = "-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif"
FONT_MONO = "'SFMono-Regular','Menlo','Consolas',monospace"

WIDTH = 840  # GitHub profile README content width

"""디자인 토큰. 파스텔 라이트 모드."""

# ---------- 컬러 시스템 ----------
# Primary: 파스텔 인디고-라벤더 (브랜드)
PRIMARY = "#7C7AED"
PRIMARY_HOVER = "#6968D9"
PRIMARY_SOFT = "#EEEEFB"
PRIMARY_DIM = "#9695F2"

# 표면 (배경 계층)
BG_BASE = "#FAFAFB"
BG_SURFACE = "#FFFFFF"
BG_ELEVATED = "#F4F4F7"
BG_SUBTLE = "#EDEDF2"

# 텍스트
TEXT_PRIMARY = "#1A1A2E"
TEXT_SECONDARY = "#5A5A72"
TEXT_TERTIARY = "#8A8AA0"
TEXT_DISABLED = "#B8B8C8"

# 보더
BORDER = "#E5E5EC"
BORDER_STRONG = "#D1D1DC"

# 상태 색
SUCCESS = "#10B981"
SUCCESS_BG = "#E7F8F1"
SUCCESS_TEXT = "#047857"

WARNING = "#F59E0B"
WARNING_BG = "#FEF4E0"
WARNING_TEXT = "#B45309"

DANGER = "#EF4444"
DANGER_BG = "#FDECEC"
DANGER_TEXT = "#B91C1C"

INFO = "#3B82F6"
INFO_BG = "#E8F0FE"
INFO_TEXT = "#1E40AF"

# 시각화 액센트
ACCENT_PEACH = "#FFB5A7"
ACCENT_MINT = "#A8E6CF"
ACCENT_LAVENDER = "#C7CEEA"
ACCENT_BUTTER = "#FFE5A0"

# ---------- 간격 ----------
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32
SPACE_10 = 40

# ---------- 모서리 ----------
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

# ---------- 폰트 ----------
FONT_FAMILY = "Pretendard"


def f_display():
    return (FONT_FAMILY, 28, "bold")


def f_title():
    return (FONT_FAMILY, 22, "bold")


def f_section():
    return (FONT_FAMILY, 16, "bold")


def f_subsection():
    return (FONT_FAMILY, 13, "bold")


def f_body():
    return (FONT_FAMILY, 13, "normal")


def f_body_medium():
    return (FONT_FAMILY, 13, "bold")


def f_caption():
    return (FONT_FAMILY, 11, "normal")


def f_caption_bold():
    return (FONT_FAMILY, 11, "bold")


def f_tiny():
    return (FONT_FAMILY, 10, "normal")


def f_label():
    return (FONT_FAMILY, 12, "normal")


def f_button():
    return (FONT_FAMILY, 13, "bold")

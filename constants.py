# ============================================================
# constants.py
# Macintosh Finder TUI  共通定数
# ============================================================

import os

HOME = os.path.expanduser("~")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------
# Trash (XDG Trash 準拠)
# ------------------------------------------------------------

_DATA_HOME = os.environ.get(
    "XDG_DATA_HOME",
    os.path.join(HOME, ".local", "share"),
)

TRASH_PATH = os.path.join(_DATA_HOME, "Trash", "files")
TRASH_INFO_PATH = os.path.join(_DATA_HOME, "Trash", "info")

# ------------------------------------------------------------
# 表示記号 (ASCII 固定: Raspberry Pi の素のコンソールでも崩れない)
# ------------------------------------------------------------

FILE_SYMBOL = "$"
DIR_SYMBOL = "#"

TRASH_SYMBOL_EMPTY = "E"
TRASH_SYMBOL_FULL = "F"

POINTER_SYMBOL = ">"

WINDOW_TL = "+"
WINDOW_TR = "+"
WINDOW_BL = "+"
WINDOW_BR = "+"
WINDOW_H = "-"
WINDOW_V = "|"

CLOSE_SYMBOL = "X"
RESIZE_SYMBOL = "+"

APPLE_SYMBOL = "A"

# ------------------------------------------------------------
# 動作設定
# ------------------------------------------------------------

# 先頭が "." のファイルをデスクトップ/ウィンドウに表示するか
# (View > Show Hidden で切り替え可能)
HIDE_DOTFILES = True

# ダブルクリック判定 (秒)。Pi Zero は描画が遅いので少し長め
DOUBLE_CLICK_TIME = 0.6

# Undo の履歴数
MAX_UNDO = 20

# Esc キーの待ち時間 (ミリ秒)
ESC_DELAY_MS = "25"

# ------------------------------------------------------------
# デスクトップ配置
# ------------------------------------------------------------

DESKTOP_MARGIN_X = 4
DESKTOP_MARGIN_Y = 5
DESKTOP_COLUMN_WIDTH = 20
DESKTOP_ROW_HEIGHT = 2

# ------------------------------------------------------------
# ウィンドウ配置 (ウィンドウ内アイコンの配置はすべてここから計算する)
# ------------------------------------------------------------

WINDOW_MARGIN_X = 2
WINDOW_MARGIN_Y = 2
WINDOW_COLUMN_WIDTH = 18
WINDOW_ROW_HEIGHT = 3

# ------------------------------------------------------------
# メッセージ
# ------------------------------------------------------------

STARTUP_MESSAGE = (
    "Macintosh 128K   "
    "WASD:move  Space:click  G:drag  Enter:open  Q:quit"
)

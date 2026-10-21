# ============================================================
# windows.py
# Finder風ウィンドウ管理
# ============================================================

import os
import curses

from filesystem import read_directory, icon_at

from constants import (
    WINDOW_MARGIN_X, WINDOW_MARGIN_Y,
    WINDOW_COLUMN_WIDTH, WINDOW_ROW_HEIGHT,
    WINDOW_TL, WINDOW_TR, WINDOW_BL, WINDOW_BR,
    WINDOW_H, WINDOW_V,
    CLOSE_SYMBOL, RESIZE_SYMBOL,
)

from textutil import put

WINDOW_LABEL_W = WINDOW_COLUMN_WIDTH - 1
MIN_WINDOW_W = 24
MIN_WINDOW_H = 7


# ============================================================
# アイコン配置 (ウィンドウ内の配置はここだけで行う)
# ============================================================

def layout_window_icons(window):

    columns = max(1, (window["w"] - 4) // WINDOW_COLUMN_WIDTH)

    for i, icon in enumerate(window["icons"]):

        icon["x"] = WINDOW_MARGIN_X + (i % columns) * WINDOW_COLUMN_WIDTH
        icon["y"] = WINDOW_MARGIN_Y + (i // columns) * WINDOW_ROW_HEIGHT

    window["scroll"] = max(
        0,
        min(window.get("scroll", 0), get_max_scroll(window)),
    )


# ============================================================
# 生成 / 更新
# ============================================================

def create_window(path, number, width, height):

    icons = read_directory(path)

    win_w = max(MIN_WINDOW_W, min(65, width - 6))
    win_w = min(win_w, max(10, width - 2))

    columns = max(1, (win_w - 4) // WINDOW_COLUMN_WIDTH)
    rows = max(1, (len(icons) + columns - 1) // columns)

    win_h = min(
        max(10, rows * WINDOW_ROW_HEIGHT + 5),
        max(MIN_WINDOW_H, height - 8),
    )
    win_h = min(win_h, max(5, height - 4))

    offset = ((number - 1) % 8) * 3

    win_x = min(6 + offset, max(1, width - win_w - 1))
    win_y = min(4 + offset, max(3, height - win_h - 1))

    window = {
        "path": path,
        "title": None,
        "icons": icons,
        "x": win_x,
        "y": win_y,
        "w": win_w,
        "h": win_h,
        "selected": None,
        "scroll": 0,
    }

    layout_window_icons(window)

    return window


def refresh_window(window):
    """ディレクトリを読み直す (選択状態はパスで引き継ぐ)"""

    selected = window["selected"]
    selected_path = selected["path"] if selected else None

    window["icons"] = read_directory(window["path"])
    window["selected"] = None

    layout_window_icons(window)

    if selected_path:
        for icon in window["icons"]:
            if icon["path"] == selected_path:
                window["selected"] = icon
                break


def clamp_window(window, width, height):
    """端末サイズ変更後に画面内へ収める"""

    window["w"] = max(10, min(window["w"], width - 2))
    window["h"] = max(5, min(window["h"], height - 4))

    window["x"] = max(1, min(window["x"], width - window["w"] - 1))
    window["y"] = max(3, min(window["y"], height - window["h"] - 1))

    layout_window_icons(window)


# ============================================================
# スクロール
# ============================================================

def get_max_scroll(window):

    icons = window["icons"]

    if not icons:
        return 0

    max_icon_y = max(icon["y"] for icon in icons)

    return max(0, max_icon_y - (window["h"] - 3))


def scroll_window(window, amount):

    if window is None:
        return

    window["scroll"] = max(
        0,
        min(window.get("scroll", 0) + amount, get_max_scroll(window)),
    )


# ============================================================
# 判定
# ============================================================

def window_title(window):

    if window.get("title"):
        return window["title"]

    return os.path.basename(window["path"]) or "/"


def point_in_window(window, x, y):

    return (
        window["x"] <= x < window["x"] + window["w"]
        and window["y"] <= y < window["y"] + window["h"]
    )


def point_in_titlebar(window, x, y):
    return point_in_window(window, x, y) and y == window["y"]


def close_button_position(window):
    return window["x"] + 1, window["y"]


def resize_handle_position(window):
    return (
        window["x"] + window["w"] - 1,
        window["y"] + window["h"] - 1,
    )


def point_on_close_button(window, x, y):
    return (x, y) == close_button_position(window)


def point_on_resize_handle(window, x, y):
    return (x, y) == resize_handle_position(window)


def window_icon_at(window, mouse_x, mouse_y, exclude=None):
    """ウィンドウ内アイコン (表示領域内のものだけ)"""

    if not (window["y"] + 1 <= mouse_y <= window["y"] + window["h"] - 3):
        return None

    local_x = mouse_x - window["x"]
    local_y = mouse_y - window["y"] + window.get("scroll", 0)

    return icon_at(
        window["icons"], local_x, local_y, WINDOW_LABEL_W, exclude)


def window_at(windows, x, y):

    for window in reversed(windows):
        if point_in_window(window, x, y):
            return window

    return None


def bring_to_front(windows, window):

    if window in windows:
        windows.remove(window)
        windows.append(window)


def close_window(windows, window):

    if window in windows:
        windows.remove(window)
        return True

    return False


def get_active_window(windows):
    return windows[-1] if windows else None


# ============================================================
# 描画
# ============================================================

def draw_window(stdscr, window, active=False):

    height, width = stdscr.getmaxyx()

    x = window["x"]
    y = window["y"]
    w = window["w"]
    h = window["h"]

    inner = " " * (w - 2)

    put(stdscr, y, x, WINDOW_TL + WINDOW_H * (w - 2) + WINDOW_TR, w)

    for row in range(y + 1, y + h - 1):
        put(stdscr, row, x, WINDOW_V + inner + WINDOW_V, w)

    put(stdscr, y + h - 1, x, WINDOW_BL + WINDOW_H * (w - 2) + WINDOW_BR, w)

    attr = curses.A_BOLD if active else 0

    put(stdscr, y, x + 1, CLOSE_SYMBOL, 1, attr)
    put(stdscr, y, x + 3, " " + window_title(window) + " ",
        max(1, w - 6), attr)

    put(stdscr, y + h - 1, x + w - 1, RESIZE_SYMBOL, 1)

    # --------------------------------------------------------
    # アイコン
    # --------------------------------------------------------

    scroll = window.get("scroll", 0)
    selected = window["selected"]

    top = y + 1
    bottom = y + h - 3

    for icon in window["icons"]:

        sy = y + icon["y"] - scroll

        if sy < top or sy > bottom:
            continue

        if icon is selected:
            text = "[{} {}]".format(icon["symbol"], icon["label"])
        else:
            text = " {} {} ".format(icon["symbol"], icon["label"])

        available = w - 1 - icon["x"]

        put(stdscr, sy, x + icon["x"], text,
            min(WINDOW_LABEL_W, available))

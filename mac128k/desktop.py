# ============================================================
# desktop.py
# Finder風デスクトップ描画 と 画面レイアウト計算
# ============================================================

import curses

from constants import (
    HOME,
    POINTER_SYMBOL,
    DESKTOP_COLUMN_WIDTH,
    WINDOW_TL, WINDOW_TR, WINDOW_BL, WINDOW_BR,
    WINDOW_H, WINDOW_V,
)

from menu import (
    MENU_ITEMS,
    draw_menu_bar,
    draw_popup_menu,
)

from windows import draw_window
from trash import trash_symbol
from textutil import put, fit, text_width

DESKTOP_LABEL_W = DESKTOP_COLUMN_WIDTH - 1
DESKTOP_TOP = 3


# ============================================================
# レイアウト計算 (描画とイベント処理で共有)
# ============================================================

def trash_origin(width, height):
    return width - 14, height - 5


def point_in_trash(width, height, x, y):

    tx, ty = trash_origin(width, height)

    return ty <= y <= ty + 1 and tx <= x < tx + 12


def desktop_bottom(height):
    """アイコンを置ける最下行 (Trash の行を避ける)"""
    return height - 6


def desktop_max_scroll(icons, height):

    if not icons:
        return 0

    return max(0, max(i["y"] for i in icons) - desktop_bottom(height))


def desktop_icon_at(state, x, y, height, exclude=None):

    scroll = state["desktop_scroll"]

    for icon in reversed(state["desktop_icons"]):

        if icon is exclude:
            continue

        sy = icon["y"] - scroll

        if sy < DESKTOP_TOP or sy > desktop_bottom(height):
            continue

        if icon["x"] <= x < icon["x"] + DESKTOP_LABEL_W and sy <= y <= sy + 1:
            return icon

    return None


def confirm_layout(width, height, dialog):

    message = dialog.get("message", "")

    w = min(max(40, text_width(message) + 8), max(20, width - 2))
    h = 7
    x = max(0, (width - w) // 2)
    y = max(0, (height - h) // 2)

    buttons = "[ Yes ]    [ No ]"
    bx = x + (w - len(buttons)) // 2

    return {
        "x": x, "y": y, "w": w, "h": h,
        "btn_y": y + 4,
        "yes": (bx, bx + 7),
        "no": (bx + 11, bx + 17),
        "buttons_x": bx,
    }


def rename_layout(width, height):

    w = max(24, min(50, width - 4))
    h = 7

    return max(0, (width - w) // 2), max(0, (height - h) // 2), w, h


def info_layout(width, height, info):

    lines = info.get("lines", [])

    w = max(24, min(56, width - 4))
    h = min(len(lines) + 7, max(8, height - 2))

    return max(0, (width - w) // 2), max(0, (height - h) // 2), w, h


# ============================================================
# 部品
# ============================================================

def draw_box(stdscr, x, y, w, h, attr=0):

    inner = " " * (w - 2)

    put(stdscr, y, x, WINDOW_TL + WINDOW_H * (w - 2) + WINDOW_TR, w, attr)

    for row in range(y + 1, y + h - 1):
        put(stdscr, row, x, WINDOW_V + inner + WINDOW_V, w, attr)

    put(stdscr, y + h - 1, x,
        WINDOW_BL + WINDOW_H * (w - 2) + WINDOW_BR, w, attr)


def draw_desktop_icons(stdscr, state):

    height, width = stdscr.getmaxyx()

    scroll = state["desktop_scroll"]
    selected = state["desktop_selected"]

    for icon in state["desktop_icons"]:

        sy = icon["y"] - scroll
        x = icon["x"]

        if sy < DESKTOP_TOP or sy > desktop_bottom(height):
            continue

        if x < 1 or x >= width - 1:
            continue

        if icon is selected:
            text = "[{} {}]".format(icon["symbol"], icon["label"])
        else:
            text = " {} {} ".format(icon["symbol"], icon["label"])

        put(stdscr, sy, x, text, min(DESKTOP_LABEL_W, width - x - 1))


def draw_trash(stdscr, selected=False):

    height, width = stdscr.getmaxyx()

    x, y = trash_origin(width, height)
    symbol = trash_symbol()

    text = "[{} Trash]" if selected else " {} Trash "

    put(stdscr, y, x, text.format(symbol), max(1, width - x - 1))


def draw_desktop_title(stdscr):

    height, width = stdscr.getmaxyx()

    put(stdscr, 2, 3, " {} ".format(HOME), max(1, width - 6))


def draw_message(stdscr, message):

    if message is None:
        return

    height, width = stdscr.getmaxyx()

    put(stdscr, height - 2, 2, str(message), max(1, width - 4))


def draw_pointer(stdscr, x, y):

    height, width = stdscr.getmaxyx()

    if 1 <= x < width - 1 and 1 <= y < height - 1:
        put(stdscr, y, x, POINTER_SYMBOL, 1, curses.A_BOLD)


# ============================================================
# ダイアログ
# ============================================================

def draw_confirm_dialog(stdscr, dialog):

    if dialog is None:
        return

    height, width = stdscr.getmaxyx()
    lay = confirm_layout(width, height, dialog)

    attr = curses.A_REVERSE

    draw_box(stdscr, lay["x"], lay["y"], lay["w"], lay["h"], attr)

    message = fit(dialog.get("message", ""), lay["w"] - 4)
    mx = lay["x"] + (lay["w"] - text_width(message)) // 2

    put(stdscr, lay["y"] + 2, mx, message, None, attr)
    put(stdscr, lay["btn_y"], lay["buttons_x"], "[ Yes ]    [ No ]",
        None, attr)

    hint = "Y / Enter : Yes     N / Esc : No"
    hx = lay["x"] + (lay["w"] - len(hint)) // 2

    put(stdscr, lay["y"] + 5, hx, hint, lay["w"] - 2, attr)


def draw_rename_dialog(stdscr, rename):

    if rename is None:
        return

    height, width = stdscr.getmaxyx()
    x, y, w, h = rename_layout(width, height)

    attr = curses.A_REVERSE

    draw_box(stdscr, x, y, w, h, attr)

    put(stdscr, y + 1, x + 2, "Rename", None, attr)

    name = rename.get("name", "")
    cursor = rename.get("cursor", len(name))
    field_w = w - 6

    # カーソルが見える範囲だけを表示する
    start = 0

    while text_width(name[start:cursor]) > field_w - 1:
        start += 1

    put(stdscr, y + 3, x + 2, fit(name[start:], field_w), field_w, attr)

    cx = x + 2 + text_width(name[start:cursor])
    cursor_ch = name[cursor] if cursor < len(name) else " "

    put(stdscr, y + 3, cx, cursor_ch, 2, curses.A_NORMAL)

    put(stdscr, y + 5, x + 2, "[ Enter ] OK    [ Esc ] Cancel",
        w - 4, attr)


def draw_info_dialog(stdscr, info):

    if info is None:
        return

    height, width = stdscr.getmaxyx()
    x, y, w, h = info_layout(width, height, info)

    attr = curses.A_REVERSE

    draw_box(stdscr, x, y, w, h, attr)

    put(stdscr, y + 1, x + 2, info.get("title", ""), w - 4, attr)

    for i, line in enumerate(info.get("lines", [])):

        if y + 3 + i >= y + h - 2:
            break

        put(stdscr, y + 3 + i, x + 3, line, w - 6, attr)

    close_text = "[ Enter / Esc ]"

    put(stdscr, y + h - 2, x + (w - len(close_text)) // 2,
        close_text, None, attr)


# ============================================================
# 画面全体
# ============================================================

def draw_screen(stdscr, state):

    stdscr.erase()
    stdscr.border()

    draw_menu_bar(stdscr, state["active_menu"])
    draw_desktop_title(stdscr)
    draw_desktop_icons(stdscr, state)
    draw_trash(stdscr, state["trash_selected"])

    for window in state["windows"]:
        draw_window(stdscr, window, window is state["active_window"])

    if state["active_menu"] is not None:
        draw_popup_menu(
            stdscr,
            state["active_menu"],
            dict(MENU_ITEMS)[state["active_menu"]],
        )

    draw_message(stdscr, state["message"])

    draw_confirm_dialog(stdscr, state["dialog"])
    draw_rename_dialog(stdscr, state["rename"])
    draw_info_dialog(stdscr, state["info"])

    # ポインタは最後 (ダイアログの上でも見えるように)
    draw_pointer(stdscr, state["mouse_x"], state["mouse_y"])

    stdscr.refresh()

# ============================================================
# menu.py
# Macintosh風メニューバー
# ============================================================

import curses

from constants import (
    APPLE_SYMBOL,
    WINDOW_TL, WINDOW_TR, WINDOW_BL, WINDOW_BR,
    WINDOW_H, WINDOW_V,
)

from textutil import put


MENU_ITEMS = [
    (APPLE_SYMBOL, 3),
    ("File", 7),
    ("Edit", 14),
    ("View", 21),
    ("Special", 29),
]

SEPARATOR = "----------------"

MENUS = {

    APPLE_SYMBOL: [
        "About This Macintosh",
        SEPARATOR,
        "Control Panel",
        "Calculator",
    ],

    "File": [
        "New Window",
        "New Folder",
        "Open",
        "Open in Editor",
        "Get Info",
        "Put Back",
        "Close",
        SEPARATOR,
        "Quit",
    ],

    "Edit": [
        "Undo",
        SEPARATOR,
        "Cut",
        "Copy",
        "Paste",
        "Rename",
        "Clear",
    ],

    "View": [
        "by Icon",
        "by Name",
        "by Date",
        SEPARATOR,
        "Clean Up",
        "Show Hidden",
    ],

    "Special": [
        "Empty Trash",
        SEPARATOR,
        "Restart",
        "Shut Down",
    ],
}


def is_separator(item):
    return item.startswith("-")


def menu_width(menu_name):

    if menu_name not in MENUS:
        return 0

    return max(len(item) for item in MENUS[menu_name]) + 4


def popup_origin(menu_name, menu_x, screen_width):
    """画面右端にはみ出さない X 座標 (描画とクリック判定で共通)"""

    width = menu_width(menu_name)

    if menu_x + width >= screen_width - 1:
        menu_x = screen_width - width - 1

    return max(1, menu_x)


def menu_at(x, y):

    if y != 1:
        return None

    for name, start_x in MENU_ITEMS:
        if start_x <= x < start_x + len(name):
            return name

    return None


def draw_menu_bar(stdscr, active_menu=None):

    height, width = stdscr.getmaxyx()

    put(stdscr, 1, 1, " " * max(1, width - 2), width - 2)

    for name, x in MENU_ITEMS:

        attr = curses.A_REVERSE if name == active_menu else 0
        put(stdscr, 1, x, name, None, attr)


def draw_popup_menu(stdscr, menu_name, menu_x):

    height, width = stdscr.getmaxyx()

    items = MENUS[menu_name]
    w = menu_width(menu_name)
    x = popup_origin(menu_name, menu_x, width)
    y = 2

    put(stdscr, y, x, WINDOW_TL + WINDOW_H * (w - 2) + WINDOW_TR, w)

    for i, item in enumerate(items):

        if is_separator(item):
            text = WINDOW_V + WINDOW_H * (w - 2) + WINDOW_V
        else:
            text = WINDOW_V + " " + item.ljust(w - 4) + " " + WINDOW_V

        put(stdscr, y + 1 + i, x, text, w)

    put(stdscr, y + len(items) + 1, x,
        WINDOW_BL + WINDOW_H * (w - 2) + WINDOW_BR, w)


def menu_item_at(menu_name, mouse_x, mouse_y, screen_width):
    """ポップアップ内の項目名 (区切り線や枠外は None)"""

    items = MENUS[menu_name]
    w = menu_width(menu_name)
    x = popup_origin(menu_name, dict(MENU_ITEMS)[menu_name], screen_width)

    index = mouse_y - 3

    if not (x <= mouse_x < x + w):
        return None

    if not (0 <= index < len(items)):
        return None

    item = items[index]

    if is_separator(item):
        return None

    return item

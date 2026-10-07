# ============================================================
# menu.py
# Macintosh風メニューバー
# ============================================================

import curses

from constants import (
    APPLE_SYMBOL,
    WINDOW_TL,
    WINDOW_TR,
    WINDOW_BL,
    WINDOW_BR,
    WINDOW_H,
    WINDOW_V,
)


# ============================================================
# メニューバー
# ============================================================

MENU_ITEMS = [
    (APPLE_SYMBOL, 3),
    ("File", 7),
    ("Edit", 14),
    ("View", 21),
    ("Special", 29),
]


# ============================================================
# メニュー内容
# ============================================================

MENUS = {

    APPLE_SYMBOL: [
        "About This Macintosh",
        "----------------",
        "Control Panel",
        "Calculator",
    ],

    "File": [
        "New Window",
        "New Folder",
        "Open",
        "Open in Editor",
        "Get Info",
        "Close",
        "----------------",
        "Quit",
    ],

    "Edit": [
        "Undo",
        "----------------",
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
        "----------------",
        "Clean Up",
    ],

    "Special": [
        "Empty Trash",
        "----------------",
        "Restart",
        "Shut Down",
    ],
}


# ============================================================
# メニュー判定
# ============================================================

def menu_at(x, y):
    """
    指定座標のメニュー名を返す
    """

    if y != 1:
        return None

    for name, start_x in MENU_ITEMS:

        if start_x <= x < start_x + len(name):
            return name

    return None


# ============================================================
# メニューバー描画
# ============================================================

def draw_menu_bar(stdscr):

    height, width = stdscr.getmaxyx()

    try:

        stdscr.addnstr(
            1,
            1,
            " " * max(1, width - 2),
            max(1, width - 2),
        )

        for name, x in MENU_ITEMS:

            stdscr.addstr(
                1,
                x,
                name,
            )

    except curses.error:
        pass


# ============================================================
# ポップアップメニュー描画
# ============================================================

def draw_popup_menu(
    stdscr,
    menu_name,
    menu_x,
):

    height, width = stdscr.getmaxyx()

    items = MENUS[menu_name]

    menu_width = (
        max(
            len(item)
            for item in items
        )
        + 4
    )

    menu_height = len(items) + 2

    if menu_x + menu_width >= width - 1:
        menu_x = (
            width
            - menu_width
            - 1
        )

    menu_y = 2

    try:

        # ----------------------------------------------------
        # 上枠
        # ----------------------------------------------------

        stdscr.addstr(
            menu_y,
            menu_x,
            WINDOW_TL
            + WINDOW_H * (menu_width - 2)
            + WINDOW_TR,
        )

        # ----------------------------------------------------
        # 本体
        # ----------------------------------------------------

        for i, item in enumerate(items):

            y = menu_y + 1 + i

            if item.startswith("-"):

                text = (
                    WINDOW_V
                    + WINDOW_H * (menu_width - 2)
                    + WINDOW_V
                )

            else:

                text = (
                    WINDOW_V
                    + " "
                    + item.ljust(
                        menu_width - 4
                    )
                    + " "
                    + WINDOW_V
                )

            stdscr.addnstr(
                y,
                menu_x,
                text,
                menu_width,
            )

        # ----------------------------------------------------
        # 下枠
        # ----------------------------------------------------

        stdscr.addstr(
            menu_y + menu_height - 1,
            menu_x,
            WINDOW_BL
            + WINDOW_H * (menu_width - 2)
            + WINDOW_BR,
        )

    except curses.error:
        pass


# ============================================================
# メニュー幅取得
# ============================================================

def menu_width(menu_name):

    if menu_name not in MENUS:
        return 0

    return (
        max(
            len(item)
            for item in MENUS[menu_name]
        )
        + 4
    )


# ============================================================
# メニュー項目取得
# ============================================================

def menu_items(menu_name):

    return MENUS.get(
        menu_name,
        [],
    )


# ============================================================
# 区切り線か判定
# ============================================================

def is_separator(item):

    return item.startswith("-")


# ============================================================
# ポップアップ内クリック判定
# ============================================================

def menu_item_at(
    menu_name,
    menu_x,
    mouse_x,
    mouse_y,
):

    items = MENUS[menu_name]

    menu_width = (
        max(
            len(item)
            for item in items
        )
        + 4
    )

    menu_y = 2

    item_index = (
        mouse_y
        - menu_y
        - 1
    )

    if not (
        menu_x <= mouse_x < menu_x + menu_width
    ):
        return None

    if not (
        0 <= item_index < len(items)
    ):
        return None

    item = items[item_index]

    if is_separator(item):
        return None

    return item


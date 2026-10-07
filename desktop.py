# ============================================================
# desktop.py
# Finder風デスクトップ描画
#
# Arch Linux / Raspberry Pi Zero 対応
# ============================================================

import curses

from constants import (
    HOME,
    POINTER_SYMBOL,
)

from menu import (
    MENU_ITEMS,
    draw_menu_bar,
    draw_popup_menu,
)

from windows import (
    draw_window,
)

from trash import (
    trash_symbol,
)


# ============================================================
# デスクトップアイコン描画
# ============================================================

def draw_desktop_icons(stdscr, icons, selected):
    height, width = stdscr.getmaxyx()

    for icon in icons:
        x = icon["x"]
        y = icon["y"]

        # 画面外のアイコンは描画しない
        if y < 1 or y >= height - 3:
            continue

        if x < 1 or x >= width - 1:
            continue

        symbol = icon.get("symbol", "")
        name = icon.get("name", "")

        if icon is selected:
            text = f"[{symbol} {name}]"
        else:
            text = f" {symbol} {name} "

        # 画面右端を絶対に越えない
        max_len = width - x - 1

        if max_len <= 0:
            continue

        try:
            stdscr.addnstr(
                y,
                x,
                text,
                max_len,
            )
        except curses.error:
            pass


# ============================================================
# Trash描画
# ============================================================

def draw_trash(
    stdscr,
    selected=False,
):

    height, width = stdscr.getmaxyx()

    trash_x = width - 14
    trash_y = height - 5

    symbol = trash_symbol()

    # --------------------------------------------------------
    # 選択状態
    # --------------------------------------------------------

    if selected:

        text = (
            f"[{symbol} Trash]"
        )

    else:

        text = (
            f" {symbol} Trash "
        )

    try:

        stdscr.addnstr(
            trash_y,
            trash_x,
            text,
            max(
                1,
                width - trash_x - 1,
            ),
        )

    except curses.error:

        pass


# ============================================================
# ウィンドウ群描画
# ============================================================

def draw_windows(
    stdscr,
    windows,
    active_window,
):

    for window in windows:

        draw_window(
            stdscr,
            window,
            window is active_window,
        )


# ============================================================
# ポインタ描画
# ============================================================

def draw_pointer(
    stdscr,
    mouse_x,
    mouse_y,
):

    height, width = stdscr.getmaxyx()

    if not (
        1 <= mouse_x < width - 1
    ):
        return

    if not (
        1 <= mouse_y < height - 1
    ):
        return

    try:

        stdscr.addch(
            mouse_y,
            mouse_x,
            POINTER_SYMBOL,
        )

    except curses.error:

        pass


# ============================================================
# メッセージ表示
# ============================================================

def draw_message(
    stdscr,
    message,
):

    height, width = stdscr.getmaxyx()

    if message is None:
        return

    try:

        stdscr.addnstr(
            height - 2,
            2,
            str(message),
            max(
                1,
                width - 4,
            ),
        )

    except curses.error:

        pass

# ============================================================
# 確認ダイアログ描画
# ============================================================

def draw_confirm_dialog(
    stdscr,
    dialog,
):

    if dialog is None:
        return

    height, width = stdscr.getmaxyx()

    message = dialog.get(
        "message",
        "",
    )

    # --------------------------------------------------------
    # ダイアログサイズ
    # --------------------------------------------------------

    dialog_w = max(
        40,
        len(message) + 8,
    )

    dialog_w = min(
        dialog_w,
        width - 4,
    )

    dialog_h = 7

    dialog_x = (
        width - dialog_w
    ) // 2

    dialog_y = (
        height - dialog_h
    ) // 2

    # --------------------------------------------------------
    # ダイアログ背景を消す
    # --------------------------------------------------------

    try:

        blank = " " * dialog_w

        for y in range(
            dialog_y,
            dialog_y + dialog_h,
        ):

            stdscr.addstr(
                y,
                dialog_x,
                blank,
            )

        # ----------------------------------------------------
        # 枠
        # ----------------------------------------------------

        stdscr.addstr(
            dialog_y,
            dialog_x,
            "┌"
            + "─" * (dialog_w - 2)
            + "┐",
        )

        for y in range(
            dialog_y + 1,
            dialog_y + dialog_h - 1,
        ):

            stdscr.addstr(
                y,
                dialog_x,
                "│",
            )

            stdscr.addstr(
                y,
                dialog_x + dialog_w - 1,
                "│",
            )

        stdscr.addstr(
            dialog_y + dialog_h - 1,
            dialog_x,
            "└"
            + "─" * (dialog_w - 2)
            + "┘",
        )

        # ----------------------------------------------------
        # メッセージ
        # ----------------------------------------------------

        message_x = (
            dialog_x
            + (
                dialog_w
                - len(message)
            ) // 2
        )

        stdscr.addstr(
            dialog_y + 2,
            message_x,
            message,
        )

        # ----------------------------------------------------
        # ボタン
        # ----------------------------------------------------

        buttons = (
            "[ Yes ]"
            + "    "
            + "[ No ]"
        )

        buttons_x = (
            dialog_x
            + (
                dialog_w
                - len(buttons)
            ) // 2
        )

        stdscr.addstr(
            dialog_y + 4,
            buttons_x,
            buttons,
        )

    except curses.error:

        pass


# ============================================================
# デスクトップタイトル
# ============================================================

def draw_desktop_title(
    stdscr,
):

    height, width = stdscr.getmaxyx()

    try:

        stdscr.addnstr(
            2,
            3,
            f" {HOME} ",
            max(
                1,
                width - 6,
            ),
        )

    except curses.error:

        pass


# ============================================================
# アクティブメニュー
# ============================================================

def draw_active_menu(
    stdscr,
    active_menu,
):

    if active_menu is None:
        return

    menu_x = dict(
        MENU_ITEMS
    )[active_menu]

    draw_popup_menu(
        stdscr,
        active_menu,
        menu_x,
    )


# ============================================================
# Finder画面全体描画
# ============================================================

def draw_screen(
    stdscr,
    desktop_icons,
    desktop_selected,
    windows,
    active_window,
    active_menu,
    trash_selected,
    mouse_x,
    mouse_y,
    message,
    dialog,
    rename,
    info,
):

    stdscr.erase()

    stdscr.border()

    draw_menu_bar(
        stdscr
    )

    draw_desktop_title(
        stdscr
    )

    draw_desktop_icons(
        stdscr,
        desktop_icons,
        desktop_selected,
    )

    draw_trash(
        stdscr,
        trash_selected,
    )

    draw_windows(
        stdscr,
        windows,
        active_window,
    )

    draw_active_menu(
        stdscr,
        active_menu,
    )

    draw_pointer(
        stdscr,
        mouse_x,
        mouse_y,
    )

    draw_message(
        stdscr,
        message,
    )
    
    draw_confirm_dialog(
        stdscr,
        dialog,
    )
    draw_rename_dialog(
        stdscr,
        rename,
    )    
    draw_info_dialog(
        stdscr,
        info,
    )

    stdscr.refresh()
# ============================================================
# Renameダイアログ
# ============================================================

def draw_rename_dialog(
    stdscr,
    rename,
):

    if rename is None:
        return

    height, width = (
        stdscr.getmaxyx()
    )

    dialog_w = 50
    dialog_h = 7

    dialog_x = (
        width - dialog_w
    ) // 2

    dialog_y = (
        height - dialog_h
    ) // 2

    try:

        # ----------------------------------------------------
        # 背景を白黒反転で塗りつぶす
        # ----------------------------------------------------

        blank = " " * dialog_w

        for y in range(
            dialog_y,
            dialog_y + dialog_h,
        ):

            stdscr.addstr(
                y,
                dialog_x,
                blank,
                curses.A_REVERSE,
            )

        # ----------------------------------------------------
        # 枠
        # ----------------------------------------------------

        stdscr.addstr(
            dialog_y,
            dialog_x,
            "+" + "-" * (dialog_w - 2) + "+",
            curses.A_REVERSE,
        )

        stdscr.addstr(
            dialog_y + dialog_h - 1,
            dialog_x,
            "+" + "-" * (dialog_w - 2) + "+",
            curses.A_REVERSE,
        )

        # ----------------------------------------------------
        # タイトル
        # ----------------------------------------------------

        stdscr.addstr(
            dialog_y + 1,
            dialog_x + 2,
            "Rename",
            curses.A_REVERSE,
        )

        # ----------------------------------------------------
        # 名前
        # ----------------------------------------------------

        name = rename.get(
            "name",
            "",
        )

        stdscr.addstr(
            dialog_y + 3,
            dialog_x + 2,
            name[:dialog_w - 6],
            curses.A_REVERSE,
        )

        # ----------------------------------------------------
        # 操作説明
        # ----------------------------------------------------

        stdscr.addstr(
            dialog_y + 5,
            dialog_x + 2,
            "[ Enter ]    [ Esc ]",
            curses.A_REVERSE,
        )

    except curses.error:

        pass
# ============================================================
# Get Info ダイアログ
# ============================================================

def draw_info_dialog(
    stdscr,
    info,
):

    if info is None:
        return

    height, width = stdscr.getmaxyx()

    dialog_w = 56
    dialog_h = 12

    dialog_w = min(
        dialog_w,
        width - 4,
    )

    dialog_h = min(
        dialog_h,
        height - 4,
    )

    dialog_x = (
        width - dialog_w
    ) // 2

    dialog_y = (
        height - dialog_h
    ) // 2

    try:

        # ----------------------------------------------------
        # 背景
        # ----------------------------------------------------

        blank = " " * dialog_w

        for y in range(
            dialog_y,
            dialog_y + dialog_h,
        ):

            stdscr.addstr(
                y,
                dialog_x,
                blank,
                curses.A_REVERSE,
            )

        # ----------------------------------------------------
        # 枠
        # ----------------------------------------------------

        stdscr.addstr(
            dialog_y,
            dialog_x,
            "┌"
            + "─" * (dialog_w - 2)
            + "┐",
            curses.A_REVERSE,
        )

        for y in range(
            dialog_y + 1,
            dialog_y + dialog_h - 1,
        ):

            stdscr.addstr(
                y,
                dialog_x,
                "│",
                curses.A_REVERSE,
            )

            stdscr.addstr(
                y,
                dialog_x + dialog_w - 1,
                "│",
                curses.A_REVERSE,
            )

        stdscr.addstr(
            dialog_y + dialog_h - 1,
            dialog_x,
            "└"
            + "─" * (dialog_w - 2)
            + "┘",
            curses.A_REVERSE,
        )

        # ----------------------------------------------------
        # タイトル
        # ----------------------------------------------------

        title = "Get Info"

        stdscr.addstr(
            dialog_y + 1,
            dialog_x + 2,
            title,
            curses.A_REVERSE,
        )

        # ----------------------------------------------------
        # 情報
        # ----------------------------------------------------

        lines = (
            "Name:     " + info.get("name", ""),
            "Kind:     " + info.get("kind", ""),
            "Location: " + info.get("location", ""),
            "Size:     " + info.get("size", ""),
            "Modified: " + info.get("modified", ""),
        )

        for i, line in enumerate(lines):

            stdscr.addstr(
                dialog_y + 3 + i,
                dialog_x + 3,
                line[:dialog_w - 6],
                curses.A_REVERSE,
            )

        # ----------------------------------------------------
        # 閉じる
        # ----------------------------------------------------

        close_text = "[ Enter / Esc ]"

        close_x = (
            dialog_x
            + (
                dialog_w
                - len(close_text)
            ) // 2
        )

        stdscr.addstr(
            dialog_y + dialog_h - 2,
            close_x,
            close_text,
            curses.A_REVERSE,
        )

    except curses.error:

        pass

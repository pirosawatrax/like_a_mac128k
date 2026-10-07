# ============================================================
# windows.py
# Finder風ウィンドウ管理
# ============================================================

import os
import curses

from filesystem import (
    read_directory,
    icon_at,
)

from constants import (
    WINDOW_MARGIN_X,
    WINDOW_MARGIN_Y,
    WINDOW_COLUMN_WIDTH,
    WINDOW_ROW_HEIGHT,
    WINDOW_TL,
    WINDOW_TR,
    WINDOW_BL,
    WINDOW_BR,
    WINDOW_H,
    WINDOW_V,
    CLOSE_SYMBOL,
    RESIZE_SYMBOL,
)


# ============================================================
# フォルダウィンドウ生成
# ============================================================

def create_window(
    path,
    number,
    width,
    height,
):
    """
    フォルダを開いて
    ウィンドウ情報を生成
    """

    icons = read_directory(path)

    # --------------------------------------------------------
    # ウィンドウ幅
    # --------------------------------------------------------

    win_w = min(
        65,
        width - 6
    )

    columns = max(
        1,
        (win_w - 6)
        // WINDOW_COLUMN_WIDTH
    )

    rows = max(
        1,
        (
            len(icons)
            + columns
            - 1
        )
        // columns
    )

    desired_h = rows * 3 + 5

    win_h = min(
        height - 8,
        max(
            10,
            desired_h,
        ),
    )

    # --------------------------------------------------------
    # 新規ウィンドウは少しずらして表示
    # --------------------------------------------------------

    offset = (number - 1) * 3

    win_x = 6 + offset
    win_y = 4 + offset

    if win_x + win_w >= width - 1:
        win_x = 3

    if win_y + win_h >= height - 1:
        win_y = 3

    # --------------------------------------------------------
    # ウィンドウ内アイコン配置
    # --------------------------------------------------------

    for i, icon in enumerate(icons):

        column = i % columns
        row = i // columns

        icon["x"] = (
            WINDOW_MARGIN_X
            + column
            * WINDOW_COLUMN_WIDTH
        )

        icon["y"] = (
            WINDOW_MARGIN_Y
            + row
            * WINDOW_ROW_HEIGHT
        )

    return {
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

# ============================================================
# ウィンドウ内アイコン取得
# ============================================================

def window_icon_at(
    window,
    mouse_x,
    mouse_y,
):
    """
    マウス座標から
    ウィンドウ内アイコン取得
    """

    local_x = (
        mouse_x
        - window["x"]
    )

    local_y = (
        mouse_y
        - window["y"]
        + window.get("scroll", 0)
    )

    return icon_at(
        window["icons"],
        local_x,
        local_y,
    )

# ============================================================
# ウィンドウの最大スクロール量
# ============================================================

def get_max_scroll(
    window,
):

    icons = window["icons"]

    if not icons:
        return 0

    # --------------------------------------------------------
    # 一番下にあるアイコンの位置
    # --------------------------------------------------------

    max_icon_y = max(
        icon["y"]
        for icon in icons
    )

    # --------------------------------------------------------
    # ウィンドウ内の表示可能高さ
    # --------------------------------------------------------

    content_height = (
        window["h"]
        - 3
    )

    # --------------------------------------------------------
    # 一番下のアイコンが
    # 表示領域に収まるようにする
    # --------------------------------------------------------

    max_scroll = (
        max_icon_y
        - content_height
        + WINDOW_ROW_HEIGHT
    )

    return max(
        0,
        max_scroll,
    )


# ============================================================
# ウィンドウをスクロール
# ============================================================

def scroll_window(
    window,
    amount,
):

    if window is None:
        return

    current = window.get(
        "scroll",
        0,
    )

    maximum = get_max_scroll(
        window
    )

    window["scroll"] = max(
        0,
        min(
            current + amount,
            maximum,
        ),
    )


# ============================================================
# ウィンドウ選択
# ============================================================

def select_icon(
    window,
    icon,
):
    """
    ウィンドウ内アイコン選択
    """

    if window is None:
        return

    window["selected"] = icon


# ============================================================
# ウィンドウタイトル取得
# ============================================================

def window_title(window):

    title = window.get(
        "title"
    )

    if title:
        return title

    folder_name = os.path.basename(
        window["path"]
    )

    if not folder_name:
        return "/"

    return folder_name


# ============================================================
# ウィンドウタイトル設定
# ============================================================

def set_window_title(
    window,
    title,
):

    window["title"] = title


# ============================================================
# 閉じるボタン位置
# ============================================================

def close_button_position(
    window,
):
    return (
        window["x"] + 1,
        window["y"],
    )


# ============================================================
# リサイズハンドル位置
# ============================================================

def resize_handle_position(
    window,
):
    return (
        window["x"]
        + window["w"]
        - 1,
        window["y"]
        + window["h"]
        - 1,
    )


# ============================================================
# ウィンドウ内判定
# ============================================================

def point_in_window(
    window,
    x,
    y,
):

    return (
        window["x"]
        <= x
        < window["x"]
        + window["w"]
        and
        window["y"]
        <= y
        < window["y"]
        + window["h"]
    )


# ============================================================
# タイトルバー判定
# ============================================================

def point_in_titlebar(
    window,
    x,
    y,
):

    return (
        point_in_window(
            window,
            x,
            y,
        )
        and
        y == window["y"]
    )


# ============================================================
# ウィンドウ描画
# ============================================================

def draw_window(
    stdscr,
    window,
    active=False,
):

    win_x = window["x"]
    win_y = window["y"]
    win_w = window["w"]
    win_h = window["h"]

    icons = window["icons"]
    selected = window["selected"]

    height, width = stdscr.getmaxyx()

    # --------------------------------------------------------
    # 背景
    # --------------------------------------------------------

    for y in range(
        win_y + 1,
        min(
            win_y + win_h - 1,
            height - 1,
        ),
    ):

        try:

            stdscr.addnstr(
                y,
                win_x,
                " " * max(1, win_w - 1),
                max(1, win_w - 1),
            )

        except curses.error:
            pass

    # --------------------------------------------------------
    # 枠
    # --------------------------------------------------------

    try:

        stdscr.addnstr(
            win_y,
            win_x,
            WINDOW_TL
            + WINDOW_H * (win_w - 2)
            + WINDOW_TR,
            win_w,
        )

        if win_y + win_h - 1 < height:

            stdscr.addnstr(
                win_y + win_h - 1,
                win_x,
                WINDOW_BL
                + WINDOW_H * (win_w - 2)
                + WINDOW_BR,
                win_w,
            )

        for y in range(
            win_y + 1,
            min(
                win_y + win_h - 1,
                height,
            ),
        ):

            stdscr.addch(
                y,
                win_x,
                WINDOW_V,
            )

            if (
                win_x
                + win_w
                - 1
                < width
            ):

                stdscr.addch(
                    y,
                    win_x + win_w - 1,
                    WINDOW_V,
                )

    except curses.error:
        pass

    # --------------------------------------------------------
    # タイトルバー
    # --------------------------------------------------------

    title = (
        " "
        + window_title(window)
        + " "
    )

    attr = (
        curses.A_BOLD
        if active
        else 0
    )

    try:

        stdscr.addnstr(
            win_y,
            win_x + 3,
            title,
            max(
                1,
                win_w - 6,
            ),
            attr,
        )

        stdscr.addch(
            win_y,
            win_x + 1,
            CLOSE_SYMBOL,
            attr,
        )

    except curses.error:
        pass

    # --------------------------------------------------------
    # リサイズハンドル
    # --------------------------------------------------------

    resize_x = (
        win_x
        + win_w
        - 1
    )

    resize_y = (
        win_y
        + win_h
        - 1
    )

    if (
        0 <= resize_x < width
        and
        0 <= resize_y < height
    ):

        try:

            stdscr.addch(
                resize_y,
                resize_x,
                RESIZE_SYMBOL,
            )

        except curses.error:
            pass

    # --------------------------------------------------------
    # アイコン表示
    # --------------------------------------------------------

    scroll = window.get(
        "scroll",
        0,
    )

    content_top = win_y + 1

    content_bottom = (
        win_y
        + win_h
        - 2
    )

    for icon in icons:

        x = (
            win_x
            + icon["x"]
        )

        y = (
            win_y
            + icon["y"]
            - scroll
        )

        # ----------------------------------------------------
        # ウィンドウの表示領域外
        # ----------------------------------------------------

        if y < content_top:
            continue

        if y >= content_bottom:
            continue

        if x < win_x + 1:
            continue

        if x >= width - 1:
            continue

        # ----------------------------------------------------
        # 選択状態
        # ----------------------------------------------------

        if icon is selected:

            text = (
                f"[{icon['symbol']} "
                f"{icon['name']}]"
            )

        else:

            text = (
                f" {icon['symbol']} "
                f"{icon['name']} "
            )

        # ----------------------------------------------------
        # ウィンドウ右端を越えない
        # ----------------------------------------------------

        max_len = min(
            len(text),
            width - x - 1,
            win_w
            - icon["x"]
            - 2,
        )

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

"""
    # --------------------------------------------------------
    # アイコン表示
    # --------------------------------------------------------

    for icon in icons:

        x = (
            win_x
            + icon["x"]
        )

        y = (
            win_y
            + icon["y"]
        )

        if y >= win_y + win_h - 2:
            continue

        if y >= height - 1:
            continue

        if x >= width - 1:
            continue

        if icon is selected:

            text = (
                f"[{icon['symbol']} "
                f"{icon['name']}]"
            )

        else:

            text = (
                f" {icon['symbol']} "
                f"{icon['name']} "
            )

        try:

            max_len = min(
                len(text),
                width - x - 1,
                win_w
                - icon["x"]
                - 2,
            )

            if max_len > 0:

                stdscr.addnstr(
                    y,
                    x,
                    text,
                    max_len,
                )

        except curses.error:
            pass

"""
# ============================================================
# ウィンドウ前面化
# ============================================================

def bring_to_front(
    windows,
    target_window,
):

    if target_window not in windows:
        return

    windows.remove(
        target_window
    )

    windows.append(
        target_window
    )


# ============================================================
# ウィンドウ閉じる
# ============================================================

def close_window(
    windows,
    target_window,
):

    if target_window in windows:

        windows.remove(
            target_window
        )

        return True

    return False


# ============================================================
# アクティブウィンドウ取得
# ============================================================

def get_active_window(
    windows,
):

    if not windows:
        return None

    return windows[-1]


# ============================================================
# 指定座標のウィンドウ取得
# ============================================================

def window_at(
    windows,
    x,
    y,
):

    for window in reversed(windows):

        if point_in_window(
            window,
            x,
            y,
        ):
            return window

    return None


# ============================================================
# 指定座標が閉じるボタン上か
# ============================================================

def point_on_close_button(
    window,
    x,
    y,
):

    close_x, close_y = (
        close_button_position(
            window
        )
    )

    return (
        x == close_x
        and
        y == close_y
    )


# ============================================================
# 指定座標がリサイズハンドル上か
# ============================================================

def point_on_resize_handle(
    window,
    x,
    y,
):

    resize_x, resize_y = (
        resize_handle_position(
            window
        )
    )

    return (
        x == resize_x
        and
        y == resize_y
    )


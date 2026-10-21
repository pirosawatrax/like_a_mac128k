# ============================================================
# main.py
# Macintosh Finder TUI
#
# Linux / Raspberry Pi Zero 対応
# ============================================================

import curses
import locale
import os

# Esc の待ち時間を短くする (curses 初期化より前に設定すること)
from constants import ESC_DELAY_MS

os.environ.setdefault("ESCDELAY", ESC_DELAY_MS)

from constants import HOME, STARTUP_MESSAGE
from filesystem import read_directory, arrange_icons
from desktop import draw_screen, desktop_max_scroll
from events import (
    handle_event,
    handle_mouse_event,
    update_mouse_position,
    any_drag,
)
from keyboard_mouse import KeyboardMouse
from windows import clamp_window


# ============================================================
# 状態
# ============================================================

def create_state(width, height):

    icons = read_directory(HOME)
    arrange_icons(icons, width, height)

    return {

        # Desktop
        "desktop_icons": icons,
        "desktop_selected": None,
        "desktop_scroll": 0,
        "trash_selected": False,

        # Windows
        "windows": [],
        "active_window": None,

        # Drag:
        #   {"kind": "desktop" | "window_icon" | "item", "icon": ..., ...}
        "drag": None,
        "dragging_window": None,
        "window_drag_offset_x": 0,
        "window_drag_offset_y": 0,
        "resizing_window": None,

        # Double click
        "last_click_key": None,
        "last_click_time": 0.0,

        # Menu / Dialogs
        "active_menu": None,
        "dialog": None,
        "rename": None,
        "info": None,

        # Edit
        "clipboard": None,
        "undo": [],

        # Mouse / Message
        "mouse_x": width // 2,
        "mouse_y": height // 2,
        "message": STARTUP_MESSAGE,

        "running": True,
    }


# ============================================================
# 端末サイズ変更
# ============================================================

def handle_resize(stdscr, state):

    height, width = stdscr.getmaxyx()

    arrange_icons(state["desktop_icons"], width, height)

    state["desktop_scroll"] = min(
        state["desktop_scroll"],
        desktop_max_scroll(state["desktop_icons"], height),
    )

    for window in state["windows"]:
        clamp_window(window, width, height)

    update_mouse_position(
        state, width, height, state["mouse_x"], state["mouse_y"])


# ============================================================
# 入力
# ============================================================

def read_key(stdscr):
    """
    (code, text) を返す。入力が無ければ None。
    text: 文字なら 1 文字の str / 特殊キーなら None
    get_wch を使うので日本語入力 (Rename) もできる。
    """

    try:
        key = stdscr.get_wch()
    except (curses.error, UnicodeDecodeError):
        return None

    if isinstance(key, str):
        return ord(key), key

    return key, None


def modal_open(state):

    return (
        state["info"] is not None
        or state["rename"] is not None
        or state["dialog"] is not None
    )


def process_key(stdscr, state, kbm, code, text):

    if code == curses.KEY_RESIZE:
        handle_resize(stdscr, state)
        return

    height, width = stdscr.getmaxyx()

    # ダイアログ表示中は WASD/G/Space を文字入力に回す
    if not modal_open(state) and code != curses.KEY_MOUSE:

        kbm.sync(state["mouse_x"], state["mouse_y"])

        consumed = True

        if kbm.move(code, width, height):
            update_mouse_position(state, width, height, kbm.x, kbm.y)

        elif code == curses.KEY_UP:
            kbm.scroll_up()

        elif code == curses.KEY_DOWN:
            kbm.scroll_down()

        elif code == ord(" "):
            kbm.click()

        elif code in (ord("g"), ord("G")):
            kbm.toggle_drag()

        else:
            consumed = False

        if consumed:
            drain_virtual_mouse(stdscr, state, kbm)
            return

    handle_event(stdscr, code, text, state)

    # Esc でドラッグ取り消し等があった場合に状態を合わせる
    kbm.heal(any_drag(state))


def drain_virtual_mouse(stdscr, state, kbm):

    while kbm.queue:
        handle_mouse_event(stdscr, state, kbm.queue.popleft())

    kbm.heal(any_drag(state))


# ============================================================
# メインループ
# ============================================================

def setup_curses(stdscr, state):

    try:
        curses.curs_set(0)
    except curses.error:
        pass

    stdscr.keypad(True)

    available, _ = curses.mousemask(
        curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    try:
        curses.mouseinterval(0)
    except curses.error:
        pass

    if not available:
        state["message"] = (
            "Mouse not available: use W/A/S/D, Space, G")


def desktop_loop(stdscr):

    height, width = stdscr.getmaxyx()

    state = create_state(width, height)
    kbm = KeyboardMouse(state["mouse_x"], state["mouse_y"])

    setup_curses(stdscr, state)

    while state["running"]:

        draw_screen(stdscr, state)

        item = read_key(stdscr)

        if item is None:
            continue

        process_key(stdscr, state, kbm, item[0], item[1])

        # 溜まっている入力 (マウス移動の連打など) をまとめて処理してから
        # 1 回だけ再描画する。Pi Zero で入力が詰まるのを防ぐ。
        stdscr.nodelay(True)

        try:

            for _ in range(200):

                if not state["running"]:
                    break

                item = read_key(stdscr)

                if item is None:
                    break

                process_key(stdscr, state, kbm, item[0], item[1])

        finally:
            stdscr.nodelay(False)


def main():

    # 日本語ファイル名の表示/入力に必要
    locale.setlocale(locale.LC_ALL, "")

    curses.wrapper(desktop_loop)


if __name__ == "__main__":
    main()

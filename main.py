# ============================================================
# main.py
# Macintosh Finder
#
# Arch Linux / Raspberry Pi Zero 対応
# ============================================================

import curses

from keyboard_mouse import (
    KeyboardMouse,
)

from constants import (
    HOME,
    STARTUP_MESSAGE,
)

from filesystem import (
    read_directory,
    arrange_icons,
)

from desktop import (
    draw_screen,
)

from events import (
    handle_event,
)

from trash import (
    make_trash_icon,
)


# ============================================================
# 状態生成
# ============================================================

def create_state(
    width,
    height,
):

    desktop_icons = read_directory(
        HOME
    )

    arrange_icons(
        desktop_icons,
        width,
        height,
    )

    # --------------------------------------------------------
    # Trashアイコン
    # --------------------------------------------------------

    trash_item = make_trash_icon(
        width - 14,
        height - 5,
    )

    return {

        # ----------------------------------------------------
        # Desktop
        # ----------------------------------------------------

        "desktop_icons":
            desktop_icons,

        "desktop_selected":
            None,

        "desktop_dragging":
            None,

        "desktop_drag_offset_x":
            0,

        "desktop_drag_offset_y":
            0,        
  
        "dragging_item": 
			None,

        "dragging_item_window": 
			None,
      
        "window_icon_dragging": None,
        "window_icon_drag_offset_x": 0,
        "window_icon_drag_offset_y": 0,

        "window_icon_press": None,

        # ----------------------------------------------------
        # Trash
        # ----------------------------------------------------

        "trash_selected":
            False,

        "trash_item":
            trash_item,

        # ----------------------------------------------------
        # Windows
        # ----------------------------------------------------

        "windows":
            [],

        "active_window":
            None,

        # ----------------------------------------------------
        # Window Move
        # ----------------------------------------------------

        "dragging_window":
            None,

        "window_drag_offset_x":
            0,

        "window_drag_offset_y":
            0,

        # ----------------------------------------------------
        # Resize
        # ----------------------------------------------------

        "resizing_window":
            None,

        # ----------------------------------------------------
        # Double Click
        # ----------------------------------------------------

        "last_clicked":
            None,

        "last_click_time":
            0,

        # ----------------------------------------------------
        # Menu
        # ----------------------------------------------------

        "active_menu":
            None,
   
        # ----------------------------------------------------
        # Dialog
        # ----------------------------------------------------

        "dialog":
            None,
        # ----------------------------------------------------
        # Rename
        # ----------------------------------------------------

        "rename":
            None,

        # ----------------------------------------------------
        # Get Info
        # ----------------------------------------------------

        "info":
            None,
        # ---------------------------------------------------
        # clipboard
        # --------------------------------------------------

        "clipboard": 
			None,

        # ----------------------------------------------------
        # Mouse
        # ----------------------------------------------------

        "mouse_x":
            width // 2,

        "mouse_y":
            height // 2,

        # ----------------------------------------------------
        # Message
        # ----------------------------------------------------

        "message":
            STARTUP_MESSAGE,

        # ----------------------------------------------------
        # Exit
        # ----------------------------------------------------

        "running":
            True,
    }


# ============================================================
# Finder Main Loop
# ============================================================

def desktop_loop(
    stdscr,
):

    curses.curs_set(0)

    curses.mousemask(
        curses.ALL_MOUSE_EVENTS
        |
        curses.REPORT_MOUSE_POSITION
    )

    try:

        curses.mouseinterval(0)

    except curses.error:

        pass

    height, width = (
        stdscr.getmaxyx()
    )

    state = create_state(
        width,
        height,
    )
    keyboard_mouse = KeyboardMouse(
        state["mouse_x"],
        state["mouse_y"],
    )
    while state["running"]:

        # ----------------------------------------------------
        # 画面描画
        # ----------------------------------------------------

        draw_screen(
            stdscr,

            state["desktop_icons"],
            state["desktop_selected"],

            state["windows"],
            state["active_window"],

            state["active_menu"],

            state["trash_selected"],

            state["mouse_x"],
            state["mouse_y"],

            state["message"],
            
            state["dialog"],
            state["rename"],
            state["info"],
        )

        # ----------------------------------------------------
        # 入力
        # ----------------------------------------------------

        key = stdscr.getch()
        
        # ------------------------------------------------
        # キーボードマウス
        # ------------------------------------------------

        if keyboard_mouse.move(
            key,
            width,
            height,
        ):

            state["mouse_x"] = (
                keyboard_mouse.x
            )

            state["mouse_y"] = (
                keyboard_mouse.y
            )

        # ------------------------------------------------
        # ↑ = ホイール上
        # ------------------------------------------------

        elif key == curses.KEY_UP:

            keyboard_mouse.scroll_up()

        # ------------------------------------------------
        # ↓ = ホイール下
        # ------------------------------------------------

        elif key == curses.KEY_DOWN:

            keyboard_mouse.scroll_down()

        # ------------------------------------------------
        # Space = 左クリック
        # ------------------------------------------------


        elif key == ord(" "):

            keyboard_mouse.click()

        # ------------------------------------------------
        # G = 左ボタン押下 / 離す
        # ------------------------------------------------

        elif key in (ord("g"), ord("G")):

            keyboard_mouse.toggle_drag()

   
        handle_event(
            stdscr,
            key,
            state,
        )       
        
      


# ============================================================
# Start
# ============================================================

def main():

    curses.wrapper(
        desktop_loop
    )


if __name__ == "__main__":

    main()


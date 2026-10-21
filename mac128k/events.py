# ============================================================
# events.py
# Finder イベント処理
#
# 構成:
#   1. 共通ヘルパー      (選択・更新・Undo)
#   2. ファイル操作      (移動・ゴミ箱・名前変更)
#   3. メニュー動作      (MENU_ACTIONS に登録)
#   4. ドラッグ処理
#   5. マウス / キーボード入力
# ============================================================

import curses
import os
import shutil
import sys
import time

from constants import (
    DOUBLE_CLICK_TIME,
    HOME,
    TRASH_PATH,
    MAX_UNDO,
)

from filesystem import (
    refresh_desktop_icons,
    arrange_icons,
    same_path,
    is_inside,
    unique_destination,
    set_show_hidden,
    show_hidden_enabled,
)

from menu import (
    APPLE_SYMBOL,
    MENU_ITEMS,
    menu_at,
    menu_item_at,
)

from windows import (
    create_window,
    refresh_window,
    layout_window_icons,
    bring_to_front,
    close_window,
    window_at,
    window_title,
    window_icon_at,
    point_in_window,
    point_in_titlebar,
    point_on_close_button,
    point_on_resize_handle,
    get_active_window,
    scroll_window,
)

from desktop import (
    point_in_trash,
    desktop_icon_at,
    desktop_max_scroll,
    confirm_layout,
    DESKTOP_TOP,
)

from trash import (
    move_to_trash,
    restore_from_trash,
    forget_trash_item,
    empty_trash,
    invalidate_cache,
)

from launcher import (
    request_launch,
    launch_file,
    edit_file,
    run_external,
)

BTN_PRESS = curses.BUTTON1_PRESSED
BTN_RELEASE = curses.BUTTON1_RELEASED
WHEEL_UP = getattr(curses, "BUTTON4_PRESSED", 0)
WHEEL_DOWN = getattr(curses, "BUTTON5_PRESSED", 0)

ENTER_KEYS = (curses.KEY_ENTER, 10, 13)


# ============================================================
# 1. 共通ヘルパー
# ============================================================

def say(state, text):
    state["message"] = text


def push_undo(state, entry):

    state["undo"].append(entry)
    del state["undo"][:-MAX_UNDO]


def clear_selection(state):

    state["desktop_selected"] = None
    state["trash_selected"] = False

    for window in state["windows"]:
        window["selected"] = None


def select_icon(state, icon, window=None):
    """選択は常に 1 つだけ"""

    clear_selection(state)

    if window is None:
        state["desktop_selected"] = icon
    else:
        window["selected"] = icon


def current_selection(state):
    """(選択中アイコン, そのウィンドウ or None)"""

    window = state["active_window"]

    if window is not None and window["selected"] is not None:
        return window["selected"], window

    if state["desktop_selected"] is not None:
        return state["desktop_selected"], None

    for window in reversed(state["windows"]):
        if window["selected"] is not None:
            return window["selected"], window

    return None, None


def is_double_click(state, key):
    """key: アイコンのパスなど。作り直されても同一判定できる"""

    now = time.monotonic()

    if (
        state["last_click_key"] == key
        and now - state["last_click_time"] < DOUBLE_CLICK_TIME
    ):
        state["last_click_key"] = None
        return True

    state["last_click_key"] = key
    state["last_click_time"] = now
    return False


def update_mouse_position(state, width, height, x, y):

    state["mouse_x"] = max(1, min(width - 2, x))
    state["mouse_y"] = max(1, min(height - 2, y))


def any_drag(state):

    return (
        state["drag"] is not None
        or state["dragging_window"] is not None
        or state["resizing_window"] is not None
    )


def cancel_drags(state):

    state["drag"] = None
    state["dragging_window"] = None
    state["resizing_window"] = None


def refresh_all(stdscr, state, select_path=None):
    """ファイル操作の後に呼ぶ。デスクトップと全ウィンドウを読み直す"""

    height, width = stdscr.getmaxyx()

    selected = state["desktop_selected"]
    selected_path = selected["path"] if selected else None

    state["desktop_icons"] = refresh_desktop_icons(
        state["desktop_icons"], width)

    state["desktop_scroll"] = min(
        state["desktop_scroll"],
        desktop_max_scroll(state["desktop_icons"], height),
    )

    state["desktop_selected"] = None

    for icon in state["desktop_icons"]:
        if icon["path"] == selected_path:
            state["desktop_selected"] = icon

    for window in list(state["windows"]):

        if os.path.isdir(window["path"]):
            refresh_window(window)
        else:
            close_window(state["windows"], window)

    if state["active_window"] not in state["windows"]:
        state["active_window"] = get_active_window(state["windows"])

    if select_path is not None:

        window = state["active_window"]
        icons = window["icons"] if window else state["desktop_icons"]

        for icon in icons:
            if icon["path"] == select_path:
                select_icon(state, icon, window)
                break

    invalidate_cache()


def update_window_paths(state, old_abs, new_abs):
    """フォルダ名変更に合わせて、開いているウィンドウのパスを更新"""

    for window in state["windows"]:

        path = os.path.abspath(window["path"])

        if path == old_abs:
            window["path"] = new_abs

        elif path.startswith(old_abs + os.sep):
            window["path"] = os.path.join(
                new_abs, os.path.relpath(path, old_abs))


def open_folder_window(stdscr, state, path):

    # すでに開いていれば前面へ
    for window in state["windows"]:
        if same_path(window["path"], path):
            bring_to_front(state["windows"], window)
            state["active_window"] = window
            return window

    height, width = stdscr.getmaxyx()

    window = create_window(
        path, len(state["windows"]) + 1, width, height)

    state["windows"].append(window)
    state["active_window"] = window

    return window


def open_icon(stdscr, state, icon):

    if icon["type"] == "folder":
        open_folder_window(stdscr, state, icon["path"])
        say(state, "Opened: " + icon["name"])
    else:
        request_launch(stdscr, state, icon["path"])


# ============================================================
# 2. ファイル操作
# ============================================================

def trash_item(stdscr, state, icon):

    name = icon["name"]
    path = icon["path"]

    if same_path(os.path.dirname(path), TRASH_PATH):
        say(state, "Already in Trash")
        return

    trashed = move_to_trash(path)

    if trashed is None:
        say(state, "Could not move to Trash: " + name)
        return

    push_undo(state, {"action": "trash", "name": trashed})
    refresh_all(stdscr, state)
    state["trash_selected"] = False
    say(state, "Moved to Trash: " + name)


def move_item(stdscr, state, icon, dest_dir, quiet_same=False):
    """icon を dest_dir へ移動する"""

    source = icon["path"]
    name = os.path.basename(source)
    source_dir = os.path.dirname(source)

    # 自分自身の上に落とした (= ただのクリック)
    if same_path(dest_dir, source):
        return

    if same_path(dest_dir, source_dir):
        say(state, "Icon moved" if quiet_same else "Already here")
        return

    if is_inside(dest_dir, source):
        say(state, "Cannot move a folder into itself")
        return

    destination = unique_destination(dest_dir, name)

    try:
        shutil.move(source, destination)
    except (OSError, shutil.Error):
        say(state, "Could not move: " + name)
        return

    if same_path(source_dir, TRASH_PATH):
        forget_trash_item(name)
    else:
        push_undo(state, {
            "action": "move",
            "source": destination,
            "destination": source,
        })

    refresh_all(stdscr, state)
    say(state, "Moved: " + os.path.basename(destination))


def drop_target(stdscr, state, x, y, dragged):
    """('trash', None) か ('dir', path)"""

    height, width = stdscr.getmaxyx()

    window = window_at(state["windows"], x, y)

    if window is not None:

        if same_path(window["path"], TRASH_PATH):
            return "trash", None

        target = window_icon_at(window, x, y, exclude=dragged)

        if target is not None and target["type"] == "folder":
            return "dir", target["path"]

        return "dir", window["path"]

    if point_in_trash(width, height, x, y):
        return "trash", None

    target = desktop_icon_at(state, x, y, height, exclude=dragged)

    if target is not None and target["type"] == "folder":
        return "dir", target["path"]

    return "dir", HOME


def commit_rename(stdscr, state):

    rename = state["rename"]
    new_name = rename["name"]

    if new_name == rename["old_name"]:
        state["rename"] = None
        say(state, "Rename cancelled")
        return

    if (
        new_name == ""
        or "/" in new_name
        or "\0" in new_name
        or new_name in (".", "..")
        or len(new_name.encode("utf-8", "replace")) > 255
    ):
        say(state, "Invalid name")
        return

    old_path = rename["path"]
    new_path = os.path.join(os.path.dirname(old_path), new_name)

    if os.path.lexists(new_path):
        say(state, "Already exists")
        return

    try:
        os.rename(old_path, new_path)
    except OSError:
        say(state, "Could not rename")
        return

    update_window_paths(
        state, os.path.abspath(old_path), os.path.abspath(new_path))

    push_undo(state, {
        "action": "rename",
        "source": new_path,
        "destination": old_path,
        "old_name": rename["old_name"],
    })

    state["rename"] = None
    refresh_all(stdscr, state, select_path=new_path)
    say(state, "Renamed: " + new_name)


# ============================================================
# 3. メニュー動作
# ============================================================

def act_about(stdscr, state):

    state["info"] = {
        "title": "About This Macintosh",
        "lines": [
            "like_a_mac128K TUI",
            "A Macintosh Finder in a terminal",
            "",
            "Python " + sys.version.split()[0],
            "ncurses " + ".".join(
                str(n) for n in curses.ncurses_version[:3]),
        ],
    }


def act_not_implemented(stdscr, state):
    say(state, "Not implemented")


def act_new_window(stdscr, state):

    open_folder_window(stdscr, state, HOME)
    say(state, "New Window")


def act_new_folder(stdscr, state):

    window = state["active_window"]
    target = window["path"] if window else HOME

    if same_path(target, TRASH_PATH):
        say(state, "Cannot create items in Trash")
        return

    name = "New Folder"
    path = os.path.join(target, name)
    number = 2

    while os.path.lexists(path):
        name = "New Folder {}".format(number)
        path = os.path.join(target, name)
        number += 1

    try:
        os.mkdir(path)
    except OSError:
        say(state, "Could not create folder")
        return

    refresh_all(stdscr, state, select_path=path)
    say(state, "Created " + name)


def act_open(stdscr, state):

    icon, window = current_selection(state)

    if icon is None:
        say(state, "No item selected")
        return

    open_icon(stdscr, state, icon)


def act_open_in_editor(stdscr, state):

    icon, window = current_selection(state)

    if icon is None:
        say(state, "No item selected")
    elif icon["type"] == "folder":
        say(state, "Cannot edit folder")
    else:
        edit_file(stdscr, state, icon["path"])


KIND_MAP = {
    ".py": "Python Source", ".sh": "Shell Script",
    ".txt": "Text Document", ".md": "Markdown Document",
    ".jpg": "JPEG Image", ".jpeg": "JPEG Image", ".png": "PNG Image",
    ".wav": "WAV Audio", ".mp3": "MP3 Audio", ".flac": "FLAC Audio",
    ".ogg": "OGG Audio", ".m4a": "M4A Audio",
    ".mp4": "MP4 Video", ".mkv": "MKV Video",
    ".webm": "WebM Video", ".avi": "AVI Video",
}


def human_size(size):

    if size < 1024:
        return "{} bytes".format(size)

    for unit in ("KB", "MB", "GB"):
        size /= 1024.0
        if size < 1024 or unit == "GB":
            return "{:.1f} {}".format(size, unit)


def act_get_info(stdscr, state):

    icon, window = current_selection(state)

    if icon is None:
        say(state, "No item selected")
        return

    path = icon["path"]
    name = os.path.basename(path)

    if os.path.isdir(path):
        kind = "Folder"
    else:
        kind = KIND_MAP.get(os.path.splitext(name)[1].lower(), "File")

    try:
        st = os.stat(path)
        size = "--" if os.path.isdir(path) else human_size(st.st_size)
        modified = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
    except OSError:
        size = "Unknown"
        modified = "Unknown"

    state["info"] = {
        "title": "Get Info",
        "lines": [
            "Name:     " + icon["label"],
            "Kind:     " + kind,
            "Location: " + os.path.dirname(path),
            "Size:     " + size,
            "Modified: " + modified,
        ],
    }

    say(state, "Get Info: " + name)


def act_put_back(stdscr, state):

    icon, window = current_selection(state)

    if (
        icon is None
        or not same_path(os.path.dirname(icon["path"]), TRASH_PATH)
    ):
        say(state, "Select an item in the Trash")
        return

    destination = restore_from_trash(icon["name"])

    if destination is None:
        say(state, "Could not Put Back: " + icon["name"])
        return

    refresh_all(stdscr, state)
    say(state, "Put Back: " + icon["name"])


def act_close(stdscr, state):

    window = state["active_window"]

    if window is None:
        say(state, "No window to close")
        return

    close_window(state["windows"], window)
    state["active_window"] = get_active_window(state["windows"])
    say(state, "Window closed")


def ask(state, message, action, **extra):

    state["dialog"] = dict(
        {"type": "confirm", "message": message, "action": action}, **extra)


def act_quit(stdscr, state):
    ask(state, "Quit Macintosh TUI?", "quit")


def act_undo(stdscr, state):

    if not state["undo"]:
        say(state, "Nothing to undo")
        return

    entry = state["undo"].pop()
    kind = entry["action"]
    ok = False

    try:

        if kind == "trash":
            ok = restore_from_trash(entry["name"]) is not None

        elif kind == "move":

            source = entry["source"]
            destination = entry["destination"]

            if os.path.lexists(source):

                directory = os.path.dirname(destination)
                os.makedirs(directory, exist_ok=True)

                shutil.move(
                    source,
                    unique_destination(
                        directory, os.path.basename(destination)),
                )
                ok = True

        elif kind == "rename":

            source = entry["source"]
            destination = entry["destination"]

            if os.path.lexists(source) and not os.path.lexists(destination):

                os.rename(source, destination)

                update_window_paths(
                    state,
                    os.path.abspath(source),
                    os.path.abspath(destination),
                )
                ok = True

        elif kind == "copy":
            # コピーの取り消し = コピーをゴミ箱へ (完全削除はしない)
            ok = move_to_trash(entry["path"]) is not None

    except (OSError, shutil.Error):
        ok = False

    if ok:
        refresh_all(stdscr, state)
        say(state, "Undo: " + kind)
    else:
        say(state, "Could not undo")


def _copy_or_cut(state, action):

    icon, window = current_selection(state)

    if icon is None:
        say(state, "No item selected")
        return

    state["clipboard"] = {"path": icon["path"], "action": action}
    say(state, ("Cut " if action == "cut" else "Copied ") + icon["name"])


def act_cut(stdscr, state):
    _copy_or_cut(state, "cut")


def act_copy(stdscr, state):
    _copy_or_cut(state, "copy")


def act_paste(stdscr, state):

    clip = state["clipboard"]

    if clip is None:
        say(state, "Nothing to paste")
        return

    source = clip["path"]

    if not os.path.lexists(source):
        state["clipboard"] = None
        say(state, "Source no longer exists")
        return

    window = state["active_window"]
    dest_dir = window["path"] if window else HOME

    if same_path(dest_dir, TRASH_PATH):
        say(state, "Cannot paste into Trash")
        return

    if same_path(dest_dir, source) or is_inside(dest_dir, source):
        say(state, "Cannot paste a folder into itself")
        return

    name = os.path.basename(source)
    source_dir = os.path.dirname(source)

    try:

        if clip["action"] == "cut":

            if same_path(source_dir, dest_dir):
                say(state, "Already here")
                return

            destination = unique_destination(dest_dir, name)
            shutil.move(source, destination)

            if same_path(source_dir, TRASH_PATH):
                forget_trash_item(name)
            else:
                push_undo(state, {
                    "action": "move",
                    "source": destination,
                    "destination": source,
                })

            state["clipboard"] = None

        else:

            destination = unique_destination(dest_dir, name)

            if os.path.isdir(source) and not os.path.islink(source):
                shutil.copytree(source, destination, symlinks=True)
            else:
                shutil.copy2(source, destination, follow_symlinks=False)

            push_undo(state, {"action": "copy", "path": destination})

    except (OSError, shutil.Error):
        say(state, "Could not paste")
        return

    refresh_all(stdscr, state, select_path=destination)
    say(state, "Pasted " + os.path.basename(destination))


def act_rename(stdscr, state):

    icon, window = current_selection(state)

    if icon is None:
        say(state, "No item selected")
        return

    if same_path(os.path.dirname(icon["path"]), TRASH_PATH):
        say(state, "Cannot rename Trash items")
        return

    state["rename"] = {
        "path": icon["path"],
        "old_name": icon["name"],
        "name": icon["name"],
        "cursor": len(icon["name"]),
    }

    say(state, "Rename: " + icon["name"])


def act_clear(stdscr, state):

    icon, window = current_selection(state)

    if icon is None:
        say(state, "No item selected")
        return

    trash_item(stdscr, state, icon)


def _sort(stdscr, state, mode):

    window = state["active_window"]
    icons = window["icons"] if window else state["desktop_icons"]

    def mtime(icon):
        try:
            return os.path.getmtime(icon["path"])
        except OSError:
            return 0

    if mode == "name":
        icons.sort(key=lambda i: i["name"].lower())
    elif mode == "date":
        icons.sort(key=lambda i: (i["type"] != "folder", -mtime(i)))
    else:
        icons.sort(key=lambda i: (i["type"] != "folder", i["name"].lower()))

    if window:
        layout_window_icons(window)
    else:
        height, width = stdscr.getmaxyx()
        arrange_icons(icons, width, height)
        state["desktop_scroll"] = 0

    say(state, "Sorted by " + mode)


def act_by_icon(stdscr, state):
    _sort(stdscr, state, "icon")


def act_by_name(stdscr, state):
    _sort(stdscr, state, "name")


def act_by_date(stdscr, state):
    _sort(stdscr, state, "date")


def act_clean_up(stdscr, state):

    window = state["active_window"]

    if window:
        layout_window_icons(window)
    else:
        height, width = stdscr.getmaxyx()
        arrange_icons(state["desktop_icons"], width, height)
        state["desktop_scroll"] = 0

    say(state, "Cleaned Up")


def act_show_hidden(stdscr, state):

    set_show_hidden(not show_hidden_enabled())
    refresh_all(stdscr, state)

    say(state, "Hidden files: " + ("shown" if show_hidden_enabled() else "hidden"))


def act_empty_trash(stdscr, state):
    ask(state, "Are you sure you want to empty the Trash?", "empty_trash")


def act_restart(stdscr, state):
    ask(state, "Are you sure you want to restart?", "restart")


def act_shutdown(stdscr, state):
    ask(state, "Are you sure you want to shut down?", "shutdown")


MENU_ACTIONS = {
    (APPLE_SYMBOL, "About This Macintosh"): act_about,
    (APPLE_SYMBOL, "Control Panel"): act_not_implemented,
    (APPLE_SYMBOL, "Calculator"): act_not_implemented,

    ("File", "New Window"): act_new_window,
    ("File", "New Folder"): act_new_folder,
    ("File", "Open"): act_open,
    ("File", "Open in Editor"): act_open_in_editor,
    ("File", "Get Info"): act_get_info,
    ("File", "Put Back"): act_put_back,
    ("File", "Close"): act_close,
    ("File", "Quit"): act_quit,

    ("Edit", "Undo"): act_undo,
    ("Edit", "Cut"): act_cut,
    ("Edit", "Copy"): act_copy,
    ("Edit", "Paste"): act_paste,
    ("Edit", "Rename"): act_rename,
    ("Edit", "Clear"): act_clear,

    ("View", "by Icon"): act_by_icon,
    ("View", "by Name"): act_by_name,
    ("View", "by Date"): act_by_date,
    ("View", "Clean Up"): act_clean_up,
    ("View", "Show Hidden"): act_show_hidden,

    ("Special", "Empty Trash"): act_empty_trash,
    ("Special", "Restart"): act_restart,
    ("Special", "Shut Down"): act_shutdown,
}


# ============================================================
# ダイアログ
# ============================================================

def run_dialog_action(stdscr, state, dialog):

    action = dialog.get("action")

    if action == "quit":
        state["running"] = False

    elif action in ("restart", "shutdown"):

        command = "reboot" if action == "restart" else "poweroff"
        ok, error = run_external(stdscr, ["sudo", command])

        say(state, command if ok else "Could not " + command + ": " + error)

    elif action == "empty_trash":

        ok = empty_trash()
        refresh_all(stdscr, state)
        say(state, "Trash emptied" if ok else "Could not empty Trash")

    elif action == "run":
        launch_file(stdscr, state, dialog["path"])


def answer_dialog(stdscr, state, yes):

    dialog = state["dialog"]
    state["dialog"] = None

    if yes:
        run_dialog_action(stdscr, state, dialog)
    else:
        say(state, "Cancelled")


def handle_dialog_click(stdscr, state, x, y):

    height, width = stdscr.getmaxyx()
    lay = confirm_layout(width, height, state["dialog"])

    if y != lay["btn_y"]:
        return

    if lay["yes"][0] <= x < lay["yes"][1]:
        answer_dialog(stdscr, state, True)

    elif lay["no"][0] <= x < lay["no"][1]:
        answer_dialog(stdscr, state, False)


# ============================================================
# 4. ドラッグ処理
# ============================================================

def start_desktop_drag(state, icon, x, y):

    state["drag"] = {
        "kind": "desktop",
        "icon": icon,
        "window": None,
        "off_x": x - icon["x"],
        "off_y": y - (icon["y"] - state["desktop_scroll"]),
        "start": (x, y),
        "moved": False,
    }


def start_window_icon_drag(state, window, icon, x, y):

    state["drag"] = {
        "kind": "window_icon",
        "icon": icon,
        "window": window,
        "off_x": x - window["x"] - icon["x"],
        "off_y": y - window["y"] + window["scroll"] - icon["y"],
        "start": (x, y),
        "moved": False,
    }


def update_drag(stdscr, state):

    drag = state["drag"]
    icon = drag["icon"]

    x = state["mouse_x"]
    y = state["mouse_y"]

    if (x, y) != drag["start"]:
        drag["moved"] = True

    height, width = stdscr.getmaxyx()

    if drag["kind"] == "desktop":

        screen_x = max(1, min(width - 8, x - drag["off_x"]))
        screen_y = max(DESKTOP_TOP, min(height - 6, y - drag["off_y"]))

        icon["x"] = screen_x
        icon["y"] = screen_y + state["desktop_scroll"]

    elif drag["kind"] == "window_icon":

        window = drag["window"]

        # ウィンドウの外へ出たら「アイコン移動」→「ファイル移動」へ切替
        if not point_in_window(window, x, y):
            drag["kind"] = "item"
            say(state, "Move: " + icon["name"])
            return

        new_x = x - window["x"] - drag["off_x"]
        new_y = y - window["y"] + window["scroll"] - drag["off_y"]

        max_y = max(i["y"] for i in window["icons"]) + 3

        icon["x"] = max(2, min(window["w"] - 10, new_x))
        icon["y"] = max(2, min(max_y, new_y))


def finish_drag(stdscr, state):

    drag = state["drag"]
    state["drag"] = None

    # 動かさずに離した = ただのクリック。何もしない
    if not drag["moved"]:
        return

    icon = drag["icon"]
    x = state["mouse_x"]
    y = state["mouse_y"]

    kind, path = drop_target(stdscr, state, x, y, icon)

    if kind == "trash":
        trash_item(stdscr, state, icon)
        return

    # アイコン位置を変えただけの場合は quiet_same
    move_item(
        stdscr, state, icon, path,
        quiet_same=(drag["kind"] in ("desktop", "window_icon")),
    )


def start_window_drag(state, window, x, y):

    state["dragging_window"] = window
    state["window_drag_offset_x"] = x - window["x"]
    state["window_drag_offset_y"] = y - window["y"]


def update_window_drag(stdscr, state):

    window = state["dragging_window"]
    height, width = stdscr.getmaxyx()

    new_x = state["mouse_x"] - state["window_drag_offset_x"]
    new_y = state["mouse_y"] - state["window_drag_offset_y"]

    window["x"] = max(1, min(width - window["w"] - 1, new_x))
    window["y"] = max(3, min(height - window["h"] - 1, new_y))


def update_resize(stdscr, state):

    window = state["resizing_window"]
    height, width = stdscr.getmaxyx()

    new_w = max(20, state["mouse_x"] - window["x"] + 1)
    new_h = max(7, state["mouse_y"] - window["y"] + 1)

    window["w"] = min(new_w, width - window["x"] - 1)
    window["h"] = min(new_h, height - window["y"] - 1)

    # 幅が変わったらアイコンを並べ直す
    layout_window_icons(window)


# ============================================================
# 5. マウス入力
# ============================================================

def handle_menu_click(stdscr, state, x, y):
    """メニューが処理したら True"""

    height, width = stdscr.getmaxyx()

    clicked = menu_at(x, y)

    if clicked is not None:
        state["active_menu"] = (
            None if state["active_menu"] == clicked else clicked)
        return True

    if state["active_menu"] is None:
        return False

    menu_name = state["active_menu"]
    state["active_menu"] = None

    item = menu_item_at(menu_name, x, y, width)

    action = MENU_ACTIONS.get((menu_name, item))

    if action is not None:
        action(stdscr, state)

    return True


def handle_window_press(stdscr, state, window, x, y):

    bring_to_front(state["windows"], window)
    state["active_window"] = window

    if point_on_close_button(window, x, y):

        name = window_title(window)
        close_window(state["windows"], window)
        state["active_window"] = get_active_window(state["windows"])
        say(state, "Closed: " + name)
        return

    if point_on_resize_handle(window, x, y):
        state["resizing_window"] = window
        say(state, "Resize window")
        return

    if point_in_titlebar(window, x, y):
        start_window_drag(state, window, x, y)
        say(state, "Move window: " + window["path"])
        return

    icon = window_icon_at(window, x, y)

    if icon is None:
        clear_selection(state)
        return

    select_icon(state, icon, window)
    say(state, "Selected: " + icon["name"])

    if is_double_click(state, icon["path"]):
        open_icon(stdscr, state, icon)
        return

    start_window_icon_drag(state, window, icon, x, y)


def handle_trash_press(stdscr, state):

    clear_selection(state)
    state["trash_selected"] = True
    state["active_window"] = None

    if is_double_click(state, "<trash>"):
        open_folder_window(stdscr, state, TRASH_PATH)
        state["trash_selected"] = False
        say(state, "Opened: Trash")


def handle_desktop_press(stdscr, state, x, y):

    height, width = stdscr.getmaxyx()

    icon = desktop_icon_at(state, x, y, height)

    clear_selection(state)
    state["active_window"] = None

    if icon is None:
        return

    select_icon(state, icon)
    say(state, "Selected: " + icon["name"])

    if is_double_click(state, icon["path"]):
        open_icon(stdscr, state, icon)
        return

    start_desktop_drag(state, icon, x, y)


def handle_press(stdscr, state, x, y):

    height, width = stdscr.getmaxyx()

    if handle_menu_click(stdscr, state, x, y):
        return

    window = window_at(state["windows"], x, y)

    if window is not None:
        handle_window_press(stdscr, state, window, x, y)
        return

    if point_in_trash(width, height, x, y):
        handle_trash_press(stdscr, state)
        return

    handle_desktop_press(stdscr, state, x, y)


def wheel(stdscr, state, x, y, direction):

    window = window_at(state["windows"], x, y)

    if window is not None:
        scroll_window(window, 3 * direction)
        return

    height, width = stdscr.getmaxyx()

    state["desktop_scroll"] = max(
        0,
        min(
            state["desktop_scroll"] + 4 * direction,
            desktop_max_scroll(state["desktop_icons"], height),
        ),
    )


def handle_mouse_event(stdscr, state, event=None):
    """
    event: (id, x, y, z, bstate)
    None のときは curses.getmouse() から読む。
    キーボードマウスは自前キューから直接ここへ渡す。
    """

    if event is None:
        try:
            event = curses.getmouse()
        except curses.error:
            return

    _, mx, my, _, bstate = event

    height, width = stdscr.getmaxyx()
    update_mouse_position(state, width, height, mx, my)

    x = state["mouse_x"]
    y = state["mouse_y"]

    # --------------------------------------------------------
    # モーダル (Get Info / Rename / 確認)
    # --------------------------------------------------------

    if state["info"] is not None:

        if bstate & BTN_PRESS:
            state["info"] = None

        return

    if state["rename"] is not None:
        return

    if state["dialog"] is not None:

        if bstate & BTN_PRESS:
            handle_dialog_click(stdscr, state, x, y)

        return

    # --------------------------------------------------------
    # ホイール
    # --------------------------------------------------------

    if bstate & WHEEL_UP:
        wheel(stdscr, state, x, y, -1)
        return

    if bstate & WHEEL_DOWN:
        wheel(stdscr, state, x, y, 1)
        return

    released = bool(bstate & BTN_RELEASE)

    # --------------------------------------------------------
    # ドラッグ中 (通常のクリック判定より先に処理)
    # --------------------------------------------------------

    if state["drag"] is not None:

        update_drag(stdscr, state)

        if released:
            finish_drag(stdscr, state)

        return

    if state["dragging_window"] is not None:

        update_window_drag(stdscr, state)

        if released:
            state["dragging_window"] = None

        return

    if state["resizing_window"] is not None:

        update_resize(stdscr, state)

        if released:
            state["resizing_window"] = None

        return

    # --------------------------------------------------------
    # ボタン押下
    # --------------------------------------------------------

    if bstate & BTN_PRESS:
        handle_press(stdscr, state, x, y)


# ============================================================
# 6. キーボード入力
# ============================================================

def handle_escape(stdscr, state):

    if any_drag(state):
        cancel_drags(state)
        say(state, "Cancelled")
        return

    if state["active_menu"] is not None:
        state["active_menu"] = None
        return

    if state["windows"]:

        state["windows"].pop()
        state["active_window"] = get_active_window(state["windows"])
        say(state, "Window closed")


def handle_rename_key(stdscr, state, code, text):

    rename = state["rename"]
    name = rename["name"]
    cursor = rename["cursor"]

    if code in ENTER_KEYS:
        commit_rename(stdscr, state)

    elif code == 27:
        state["rename"] = None
        say(state, "Rename cancelled")

    elif code in (curses.KEY_BACKSPACE, 127, 8):

        if cursor > 0:
            rename["name"] = name[:cursor - 1] + name[cursor:]
            rename["cursor"] = cursor - 1

    elif code == curses.KEY_DC:
        rename["name"] = name[:cursor] + name[cursor + 1:]

    elif code == curses.KEY_LEFT:
        rename["cursor"] = max(0, cursor - 1)

    elif code == curses.KEY_RIGHT:
        rename["cursor"] = min(len(name), cursor + 1)

    elif code == curses.KEY_HOME:
        rename["cursor"] = 0

    elif code == curses.KEY_END:
        rename["cursor"] = len(name)

    elif text and text.isprintable():
        # 日本語など ASCII 以外も入力可能
        rename["name"] = name[:cursor] + text + name[cursor:]
        rename["cursor"] = cursor + len(text)


def handle_event(stdscr, code, text, state):
    """
    code: キーコード (get_wch の結果を int 化したもの)
    text: 文字入力なら 1 文字の str、特殊キーなら None
    """

    # 実マウスのイベントは常に読み取る (モーダル中も消費する)
    if code == curses.KEY_MOUSE:
        handle_mouse_event(stdscr, state)
        return

    if state["info"] is not None:

        if code in ENTER_KEYS or code == 27:
            state["info"] = None
            say(state, "Get Info closed")

        return

    if state["rename"] is not None:
        handle_rename_key(stdscr, state, code, text)
        return

    if state["dialog"] is not None:

        if code in ENTER_KEYS or code in (ord("y"), ord("Y")):
            answer_dialog(stdscr, state, True)

        elif code in (27, ord("n"), ord("N")):
            answer_dialog(stdscr, state, False)

        return

    if code in (ord("q"), ord("Q")):
        act_quit(stdscr, state)

    elif code == 27:
        handle_escape(stdscr, state)

    elif code in ENTER_KEYS:
        act_open(stdscr, state)

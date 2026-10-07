# ============================================================
# events.py
# Finderイベント処理
# ============================================================

import curses
import time
import os
import shutil
import sys
import subprocess
import shlex

from constants import (
    DOUBLE_CLICK_TIME,
    TRASH_PATH,
    HOME,
)

from menu import (
    menu_at,
    menu_item_at,
    MENU_ITEMS,
)

from windows import (
    create_window,
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

from filesystem import (
    icon_at,
    read_directory,
    arrange_icons,
)

from trash import (
    move_to_trash,
    restore_from_trash,
    empty_trash,
)


# ============================================================
# ダブルクリック判定
# ============================================================

def is_double_click(
    state,
    icon,
):

    now = time.monotonic()

    if (
        state["last_clicked"] is icon
        and
        now - state["last_click_time"]
        < DOUBLE_CLICK_TIME
    ):

        state["last_clicked"] = None

        return True

    state["last_clicked"] = icon
    state["last_click_time"] = now

    return False


# ============================================================
# Esc
# ============================================================

def handle_escape(
    state,
):

    if state["active_menu"] is not None:

        state["active_menu"] = None

        state["message"] = (
            "Menu closed"
        )

        return

    if state["windows"]:

        state["dragging_window"] = None

        state["resizing_window"] = None

        state["windows"].pop()

        state["active_window"] = (
            get_active_window(
                state["windows"]
            )
        )

        state["message"] = (
            "Window closed"
        )


# ============================================================
# マウス位置更新
# ============================================================

def update_mouse_position(
    state,
    width,
    height,
    mouse_x,
    mouse_y,
):

    state["mouse_x"] = max(
        1,
        min(
            width - 2,
            mouse_x,
        ),
    )

    state["mouse_y"] = max(
        1,
        min(
            height - 2,
            mouse_y,
        ),
    )


# ============================================================
# Trash判定
# ============================================================

def point_in_trash(
    width,
    height,
    mouse_x,
    mouse_y,
):

    trash_x = width - 14
    trash_y = height - 5

    return (
        trash_y <= mouse_y <= trash_y + 1
        and
        trash_x <= mouse_x < trash_x + 12
    )


# ============================================================
# デスクトップアイコン移動開始
# ============================================================

def start_desktop_drag(
    state,
    icon,
    mouse_x,
    mouse_y,
):

    state["desktop_dragging"] = icon

    state["desktop_drag_offset_x"] = (
        mouse_x
        - icon["x"]
    )

    state["desktop_drag_offset_y"] = (
        mouse_y
        - icon["y"]
    )

    state["message"] = (
        "Move: "
        + icon["name"]
    )

# ============================================================
# ファイルを起動
# ============================================================

def launch_file(
    state,
    path,
):

    if not os.path.isfile(path):

        state["message"] = (
            "Not a file"
        )

        return False

    name = os.path.basename(path)

    # --------------------------------------------------------
    # 画像
    # --------------------------------------------------------

    if path.lower().endswith(
        (".jpg", ".jpeg", ".png")
    ):

        image_path = shlex.quote(path)

        shell_command = (
            "chafa "
            + image_path
            + "; "
            + "echo; "
            + "echo 'Press Enter to close'; "
            + "read"
        )

        command = [
            "tmux",
            "new-window",
            "bash",
            "-c",
            shell_command,
        ]

    # --------------------------------------------------------
    # 動画
    # --------------------------------------------------------

    elif path.lower().endswith(
        (".mp4", ".mkv", ".webm", ".avi")
    ):

        video_script = os.path.expanduser(
            "~/mac128k/chafa_video.sh"
        )

        command = [
            "tmux",
            "new-window",
            video_script,
            path,
        ]

    # --------------------------------------------------------
    # 音声
    # --------------------------------------------------------

    elif path.lower().endswith(
        (".wav", ".mp3", ".flac", ".ogg", ".m4a")
    ):

        command = [
            "tmux",
            "new-window",
            "mpv",
            "--no-video",
            path,
        ]

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    elif path.lower().endswith(".py"):

        shell_command = (
            "python3 "
            + shlex.quote(path)
            + "; "
            + "status=$?; "
            + "echo; "
            + "echo '================================'; "
            + "echo \"Python finished (exit code: $status)\"; "
            + "echo '================================'; "
            + "echo; "
            + "echo 'Press Enter to close'; "
            + "read"
        )

        command = [
            "tmux",
            "new-window",
            "bash",
            "-c",
            shell_command,
        ]

    # --------------------------------------------------------
    # テキスト
    # --------------------------------------------------------

    elif path.lower().endswith(
        (".txt", ".md", ".ini", ".conf", ".cfg", ".log", ".csv")
    ):

        command = [
            "tmux",
            "new-window",
            "nano",
            path,
        ]

    # --------------------------------------------------------
    # Shell script
    # --------------------------------------------------------

    elif path.lower().endswith(".sh"):

        shell_command = (
            "bash "
            + shlex.quote(path)
            + "; "
            + "status=$?; "
            + "echo; "
            + "echo '================================'; "
            + "echo \"Shell script finished (exit code: $status)\"; "
            + "echo '================================'; "
            + "echo; "
            + "echo 'Press Enter to close'; "
            + "read"
        )

        command = [
            "tmux",
            "new-window",
            "bash",
            "-c",
            shell_command,
        ]

    # --------------------------------------------------------
    # 実行ファイル
    # --------------------------------------------------------

    elif os.access(path, os.X_OK):

        shell_command = (
            shlex.quote(path)
            + "; "
            + "status=$?; "
            + "echo; "
            + "echo '================================'; "
            + "echo \"Program finished (exit code: $status)\"; "
            + "echo '================================'; "
            + "echo; "
            + "echo 'Press Enter to close'; "
            + "read"
        )

        command = [
            "tmux",
            "new-window",
            "bash",
            "-c",
            shell_command,
        ]

    else:

        state["message"] = (
            "Not executable: "
            + name
        )

        return False

    # --------------------------------------------------------
    # 起動
    # --------------------------------------------------------

    try:

        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        state["message"] = (
            "Launched: "
            + name
        )

        return True

    except OSError:

        state["message"] = (
            "Could not launch: "
            + name
        )

        return False
# ============================================================
# テキストファイルをEditorで開く
# ============================================================

def edit_file(
    state,
    path,
):

    if not os.path.isfile(path):

        state["message"] = (
            "Not a file"
        )

        return False

    name = os.path.basename(path)

    # --------------------------------------------------------
    # 編集可能な拡張子
    # --------------------------------------------------------

    editable_extensions = (
        ".py",
        ".sh",
        ".txt",
        ".md",
        ".ini",
        ".conf",
        ".cfg",
        ".log",
        ".csv",
        ".json",
        ".xml",
        ".html",
        ".css",
    )

    if not path.lower().endswith(
        editable_extensions
    ):

        state["message"] = (
            "Cannot edit: "
            + name
        )

        return False

    # --------------------------------------------------------
    # nano
    # --------------------------------------------------------

    command = [
        "tmux",
        "new-window",
        "nano",
        path,
    ]

    try:

        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        state["message"] = (
            "Editing: "
            + name
        )

        return True

    except OSError:

        state["message"] = (
            "Could not edit: "
            + name
        )

        return False

# ============================================================
# アイテムのドラッグ開始
# ============================================================

def start_item_drag(
    state,
    icon,
    window,
):

    state["dragging_item"] = icon
    state["dragging_item_window"] = window

    state["message"] = (
        "Move: "
        + icon["name"]
    )

# ============================================================
# ウィンドウ内アイコンのドラッグ開始
# ============================================================

def start_window_icon_drag(
    state,
    window,
    icon,
    mouse_x,
    mouse_y,
):
   
   
    scroll = window.get("scroll", 0)

    state["window_icon_dragging"] = {
        "window": window,
        "icon": icon,
    }

    state["window_icon_drag_offset_x"] = (
        mouse_x
        - window["x"]
        - icon["x"]
    )
    
   
    
    state["window_icon_drag_offset_y"] = (
        mouse_y
        - window["y"]
        + scroll
        - icon["y"]
    )
  
# ============================================================
# ウィンドウ内アイコンをドラッグ中
# ============================================================

def update_window_icon_drag(
    state,
):

    drag = state["window_icon_dragging"]

    if drag is None:
        return

    window = drag["window"]
    icon = drag["icon"]

    mouse_x = state["mouse_x"]
    mouse_y = state["mouse_y"]

    new_x = (
        mouse_x
        - window["x"]
        - state["window_icon_drag_offset_x"]
    )

    scroll = window.get("scroll", 0)
    
    new_y = (
        mouse_y
        - window["y"]
        + scroll
        - state["window_icon_drag_offset_y"]
    )
 
    # --------------------------------------------------------
    # ウィンドウ内から外へ出ないようにする
    # --------------------------------------------------------

    min_x = 2
    min_y = 2

    max_x = window["w"] - 3

    content_max_y = max(
        item["y"]
        for item in window["icons"]
    )

    max_y = content_max_y + 3

    new_x = max(
        min_x,
        min(
            new_x,
            max_x,
        ),
    )

    new_y = max(
        min_y,
        min(
            new_y,
            max_y,
        ),
    )

    icon["x"] = new_x
    icon["y"] = new_y

  

# ============================================================
# ドロップ先フォルダを取得
# ============================================================


def folder_at_drop_position(
    state,
    mouse_x,
    mouse_y,
):

    # --------------------------------------------------------
    # ウィンドウ上か確認
    # --------------------------------------------------------

    window = window_at(
        state["windows"],
        mouse_x,
        mouse_y,
    )

    # --------------------------------------------------------
    # ウィンドウ上
    # --------------------------------------------------------

    if window is not None:

        # --------------------------------------------
        # フォルダの上なら、そのフォルダへ
        # --------------------------------------------

        icon = window_icon_at(
            window,
            mouse_x,
            mouse_y,
        )

        if (
            icon is not None
            and
            icon["type"] == "folder"
        ):

            return icon["path"]

        # --------------------------------------------
        # 空白部分なら、
        # そのウィンドウが表示しているフォルダへ
        # --------------------------------------------

        return window["path"]

    # --------------------------------------------------------
    # デスクトップ上
    # --------------------------------------------------------

    icon = icon_at(
        state["desktop_icons"],
        mouse_x,
        mouse_y,
    )

    # --------------------------------------------------------
    # デスクトップ上のフォルダ
    # --------------------------------------------------------

    if (
        icon is not None
        and
        icon["type"] == "folder"
    ):

        return icon["path"]

    # --------------------------------------------------------
    # デスクトップの空白
    #
    # → HOMEへ移動
    # --------------------------------------------------------

    return HOME



# ============================================================
# アイテムをフォルダへドロップ
# ============================================================

def drop_item_on_folder(
    state,
    width,
    height,
):

    icon = state["dragging_item"]

    if icon is None:
        return

    mouse_x = state["mouse_x"]
    mouse_y = state["mouse_y"]

    destination_dir = folder_at_drop_position(
        state,
        mouse_x,
        mouse_y,
    )

    if destination_dir is None:

        state["message"] = (
            "Move cancelled"
        )

        return

    source = icon["path"]

    source_dir = os.path.dirname(
        source
    )

    # --------------------------------------------------------
    # 同じフォルダへのドロップ
    # --------------------------------------------------------

    if os.path.abspath(
        source_dir
    ) == os.path.abspath(
        destination_dir
    ):

        state["message"] = (
            "Already here"
        )

        return

    # --------------------------------------------------------
    # 移動先に同名ファイルがある場合
    # --------------------------------------------------------

    name = os.path.basename(
        source
    )

    destination = os.path.join(
        destination_dir,
        name,
    )

    if os.path.exists(destination):

        base, extension = os.path.splitext(
            name
        )

        number = 2

        while os.path.exists(
            destination
        ):

            if extension:

                new_name = (
                    base
                    + " copy "
                    + str(number)
                    + extension
                )

            else:

                new_name = (
                    base
                    + " copy "
                    + str(number)
                )

            destination = os.path.join(
                destination_dir,
                new_name,
            )

            number += 1

    # --------------------------------------------------------
    # 移動
    # --------------------------------------------------------

    try:

        shutil.move(
            source,
            destination,
        )

    except OSError:

        state["message"] = (
            "Could not move: "
            + name
        )

        return

    # --------------------------------------------------------
    # Undo情報を保存
    # --------------------------------------------------------

    state["undo"] = {
        "action": "move",
        "source": destination,
        "destination": source,
        "name": os.path.basename(destination),
    }
  
    # --------------------------------------------------------
    # デスクトップを更新
    # --------------------------------------------------------

    state["desktop_icons"] = (
        read_directory(HOME)
    )

    print(
        "DEBUG desktop_icons:",
        len(state["desktop_icons"]),
        file=sys.stderr
    )
    
    state["message"] = (
        "Desktop icons: "
        + str(len(state["desktop_icons"]))
    )
    
    arrange_icons(
        state["desktop_icons"],
        width,
        height,
    )

 


    state["desktop_selected"] = None

    # --------------------------------------------------------
    # 関係するウィンドウを更新
    # --------------------------------------------------------

    source_path = os.path.abspath(
        source_dir
    )

    destination_path = os.path.abspath(
        destination_dir
    )

    for window in state["windows"]:

        window_path = os.path.abspath(
            window["path"]
        )

        if (
            window_path == source_path
            or
            window_path == destination_path
        ):

            window["icons"] = (
                read_directory(
                    window["path"]
                )
            )

            window_w = window["w"]

            columns = max(
                1,
                (window_w - 4) // 18
            )

            for i, item in enumerate(
                window["icons"]
            ):

                column = i % columns
                row = i // columns

                item["x"] = (
                    2
                    + column * 18
                )

                item["y"] = (
                    2
                    + row * 3
                )

            window["selected"] = None

    state["message"] = (
        "Moved: "
        + os.path.basename(destination)
    )

# ============================================================
# デスクトップアイコン移動中
# ============================================================

def update_desktop_drag(
    state,
    width,
    height,
):

    icon = state["desktop_dragging"]

    if icon is None:
        return

    new_x = (
        state["mouse_x"]
        - state["desktop_drag_offset_x"]
    )

    new_y = (
        state["mouse_y"]
        - state["desktop_drag_offset_y"]
    )

    # --------------------------------------------------------
    # 画面外へ出ないようにする
    # --------------------------------------------------------

    new_x = max(
        1,
        min(
            width - 8,
            new_x,
        ),
    )

    new_y = max(
        3,
        min(
            height - 4,
            new_y,
        ),
    )

    icon["x"] = new_x
    icon["y"] = new_y


# ============================================================
# デスクトップアイコンをドロップ
# ============================================================

def drop_desktop_icon(
    state,
    width,
    height,
):

    icon = state["desktop_dragging"]

    if icon is None:
        return

    mouse_x = state["mouse_x"]
    mouse_y = state["mouse_y"]

    # --------------------------------------------------------
    # Trashへのドロップ
    # --------------------------------------------------------

    if point_in_trash(
        width,
        height,
        mouse_x,
        mouse_y,
    ):

        name = icon["name"]
        path = icon["path"]

        if move_to_trash(path):
            
            # ------------------------------------------------
            # Undo情報を保存
            # ------------------------------------------------

            state["undo"] = {
                "action": "move_to_trash",
                "source": path,
                "name": name,
            }
            
            if icon in state["desktop_icons"]:

                state["desktop_icons"].remove(
                    icon
                )

            if state["desktop_selected"] is icon:

                state["desktop_selected"] = None

            state["trash_selected"] = False

            state["message"] = (
                "Moved to Trash: "
                + name
            )

        else:

            state["message"] = (
                "Could not move to Trash: "
                + name
            )

        return

    # --------------------------------------------------------
    # フォルダへのドロップ
    # --------------------------------------------------------

    destination_dir = folder_at_drop_position(
        state,
        mouse_x,
        mouse_y,
    )

    # フォルダではない場所なら
    # デスクトップ上でアイコンを動かしただけ
    if destination_dir is None:

        state["message"] = (
            "Desktop icon moved"
        )

        return

    source = icon["path"]

    source_dir = os.path.dirname(
        source
    )

    # --------------------------------------------------------
    # 同じフォルダへのドロップ
    # --------------------------------------------------------

    if os.path.abspath(
        source_dir
    ) == os.path.abspath(
        destination_dir
    ):

        state["message"] = (
            "Already here"
        )

        return

    # --------------------------------------------------------
    # 移動先のファイル名
    # --------------------------------------------------------

    name = os.path.basename(
        source
    )

    destination = os.path.join(
        destination_dir,
        name,
    )

    if os.path.exists(destination):

        base, extension = os.path.splitext(
            name
        )

        number = 2

        while os.path.exists(
            destination
        ):

            if extension:

                new_name = (
                    base
                    + " copy "
                    + str(number)
                    + extension
                )

            else:

                new_name = (
                    base
                    + " copy "
                    + str(number)
                )

            destination = os.path.join(
                destination_dir,
                new_name,
            )

            number += 1

    # --------------------------------------------------------
    # 移動
    # --------------------------------------------------------

    try:

        shutil.move(
            source,
            destination,
        )

    except OSError:

        state["message"] = (
            "Could not move: "
            + name
        )

        return
    # --------------------------------------------------------
    # Undo情報を保存
    # --------------------------------------------------------

    state["undo"] = {
        "action": "move",
        "source": destination,
        "destination": source,
        "name": os.path.basename(destination),
    }
    # --------------------------------------------------------
    # デスクトップ更新
    # --------------------------------------------------------

    state["desktop_icons"] = (
        read_directory(HOME)
    )

    arrange_icons(
        state["desktop_icons"],
        width,
        height,
    )

    state["desktop_selected"] = None

    # --------------------------------------------------------
    # 移動先が開いているウィンドウなら更新
    # --------------------------------------------------------

    destination_path = os.path.abspath(
        destination_dir
    )

    for window in state["windows"]:

        window_path = os.path.abspath(
            window["path"]
        )

        if window_path == destination_path:

            window["icons"] = (
                read_directory(
                    window["path"]
                )
            )

            window_w = window["w"]

            columns = max(
                1,
                (window_w - 4) // 18
            )

            for i, item in enumerate(
                window["icons"]
            ):

                column = i % columns
                row = i // columns

                item["x"] = (
                    2
                    + column * 18
                )

                item["y"] = (
                    2
                    + row * 3
                )

            window["selected"] = None

    state["message"] = (
        "Moved: "
        + os.path.basename(destination)
    )


# ============================================================
# ウィンドウ移動開始
# ============================================================

def start_window_drag(
    state,
    window,
    mouse_x,
    mouse_y,
):

    state["dragging_window"] = window

    state["window_drag_offset_x"] = (
        mouse_x
        - window["x"]
    )

    state["window_drag_offset_y"] = (
        mouse_y
        - window["y"]
    )

    state["message"] = (
        "Move window: "
        + window["path"]
    )


# ============================================================
# ウィンドウ移動中
# ============================================================

def update_window_drag(
    state,
    width,
    height,
):

    window = state["dragging_window"]

    if window is None:
        return

    new_x = (
        state["mouse_x"]
        - state["window_drag_offset_x"]
    )

    new_y = (
        state["mouse_y"]
        - state["window_drag_offset_y"]
    )

    new_x = max(
        1,
        min(
            width
            - window["w"]
            - 1,
            new_x,
        ),
    )

    new_y = max(
        3,
        min(
            height
            - window["h"]
            - 1,
            new_y,
        ),
    )

    window["x"] = new_x
    window["y"] = new_y


# ============================================================
# ウィンドウリサイズ開始
# ============================================================

def start_resize(
    state,
    window,
):

    state["resizing_window"] = window

    state["message"] = (
        "Resize window"
    )


# ============================================================
# ウィンドウリサイズ中
# ============================================================

def update_resize(
    state,
    width,
    height,
):

    window = state["resizing_window"]

    if window is None:
        return

    new_w = (
        state["mouse_x"]
        - window["x"]
        + 1
    )

    new_h = (
        state["mouse_y"]
        - window["y"]
        + 1
    )

    new_w = max(
        20,
        new_w,
    )

    new_h = max(
        7,
        new_h,
    )

    new_w = min(
        new_w,
        width
        - window["x"]
        - 1,
    )

    new_h = min(
        new_h,
        height
        - window["y"]
        - 1,
    )

    window["w"] = new_w
    window["h"] = new_h


def handle_window_click(

    state,
    window,
    mouse_x,
    mouse_y,
    width,
    height,
):
   
    
    bring_to_front(
        state["windows"],
        window,
    )

    state["active_window"] = (
        get_active_window(
            state["windows"]
        )
    )

    if point_on_close_button(
        window,
        mouse_x,
        mouse_y,
    ):

        name = window_title(window)

        close_window(
            state["windows"],
            window,
        )

        state["active_window"] = (
            get_active_window(
                state["windows"]
            )
        )

        state["message"] = (
            "Closed: "
            + name
        )

        return

    if point_on_resize_handle(
        window,
        mouse_x,
        mouse_y,
    ):

        start_resize(
            state,
            window,
        )

        return

    if point_in_titlebar(
        window,
        mouse_x,
        mouse_y,
    ):

        start_window_drag(
            state,
            window,
            mouse_x,
            mouse_y,
        )

        return

    icon = window_icon_at(
        window,
        mouse_x,
        mouse_y,
    )

    if icon is None:
        return

    window["selected"] = icon

    state["message"] = (
        "Selected: "
        + icon["name"]
    )

    # --------------------------------------------------------
    # ダブルクリック判定
    # --------------------------------------------------------

    double_click = is_double_click(
        state,
        icon,
    )

   
   
    if double_click:

        state["window_icon_press"] = None

   
    else:
        start_window_icon_drag(
            state,
            window,
            icon,
            mouse_x,
            mouse_y,
        )
        
        return     


    # --------------------------------------------------------
    # Trash の中身を元の場所へ戻す
    # --------------------------------------------------------

    if window["path"] == TRASH_PATH:

        name = icon["name"]

        if restore_from_trash(name):

            # ------------------------------------------------
            # Trashウィンドウを更新
            # ------------------------------------------------

            window["icons"] = read_directory(
                TRASH_PATH
            )

            window["selected"] = None

            # ------------------------------------------------
            # デスクトップも更新
            # ------------------------------------------------

            state["desktop_icons"] = read_directory(
                HOME
            )

            # ------------------------------------------------
            # デスクトップアイコン位置を再配置
            # ------------------------------------------------

            arrange_icons(
                state["desktop_icons"],
                width,
                height,
            )

            state["message"] = (
                "Put Back: "
                + name
            )

        else:

            state["message"] = (
                "Could not Put Back: "
                + name
            )

        return

    # --------------------------------------------------------
    # ファイル
    # --------------------------------------------------------

    if icon["type"] == "file":

        launch_file(
            state,
            icon["path"],
        )

        return

    # --------------------------------------------------------
    # フォルダ以外
    # --------------------------------------------------------

    if icon["type"] != "folder":
        return

    # --------------------------------------------------------
    # フォルダを開く
    # --------------------------------------------------------

    new_window = create_window(
        icon["path"],
        len(
            state["windows"]
        ) + 1,
        width,
        height,
    )

    state["windows"].append(
        new_window
    )

    state["active_window"] = (
        new_window
    )

    state["message"] = (
        "Opened: "
        + icon["name"]
    )


# ============================================================
# デスクトップクリック
# ============================================================

def handle_desktop_click(
    state,
    mouse_x,
    mouse_y,
    width,
    height,
):

    icon = icon_at(
        state["desktop_icons"],
        mouse_x,
        mouse_y,
    )

    if icon is None:
        return

    state["desktop_selected"] = icon

    state["message"] = (
        "Selected: "
        + icon["name"]
    )

    # --------------------------------------------------------
    # ダブルクリック
    # --------------------------------------------------------

    if is_double_click(
        state,
        icon,
    ):

        # ----------------------------------------------------
        # フォルダ
        # ----------------------------------------------------

        if icon["type"] == "folder":

            new_window = create_window(
                icon["path"],
                len(
                    state["windows"]
                ) + 1,
                width,
                height,
            )

            state["windows"].append(
                new_window
            )

            state["active_window"] = (
                new_window
            )

            state["message"] = (
                "Opened: "
                + icon["name"]
            )

            return

        # ----------------------------------------------------
        # 実行ファイル
        # ----------------------------------------------------

        if icon["type"] == "file":

            launch_file(
                state,
                icon["path"],
            )

            return

    # --------------------------------------------------------
    # ドラッグ開始
    # --------------------------------------------------------

    start_desktop_drag(
        state,
        icon,
        mouse_x,
        mouse_y,
    )


# ============================================================
# メニュークリック
# ============================================================

def handle_menu_click(
    state,
    mouse_x,
    mouse_y,
    width, 
    height,
):

    # --------------------------------------------------------
    # メニューバーをクリック
    # --------------------------------------------------------

    clicked_menu = menu_at(
        mouse_x,
        mouse_y,
    )

    if clicked_menu is not None:

        state["active_menu"] = (
            clicked_menu
        )

        return True

    # --------------------------------------------------------
    # ポップアップメニューが開いている場合
    # --------------------------------------------------------

    if state["active_menu"] is not None:

        menu_name = state["active_menu"]

        item = menu_item_at(
            menu_name,
            dict(MENU_ITEMS)[menu_name],
            mouse_x,
            mouse_y,
        )

        
        # ----------------------------------------------------
        # File → Close
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "Close"
        ):

            target_window = state["active_window"]

            if target_window is not None:

                if close_window(
                    state["windows"],
                    target_window,
                ):

                    state["active_window"] = (
                        get_active_window(
                            state["windows"]
                        )
                    )

                    state["message"] = (
                        "Window closed"
                    )

            else:

                state["message"] = (
                    "No window to close"
                )

            state["active_menu"] = None

            return True
        
        # ----------------------------------------------------
        # File → New Window
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "New Window"
        ):

            new_window = create_window(
                HOME,
                len(
                    state["windows"]
                ) + 1,
                width,
                height,
            )

            state["windows"].append(
                new_window
            )

            state["active_window"] = (
                new_window
            )

            state["message"] = (
                "New Window"
            )

            state["active_menu"] = None

            return True
        # ----------------------------------------------------
        # File → New Folder
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "New Folder"
        ):

            # ------------------------------------------------
            # 作成場所を決める
            # ------------------------------------------------

            if state["active_window"] is not None:

                target_dir = (
                    state["active_window"]["path"]
                )

            else:

                target_dir = HOME

            # ------------------------------------------------
            # フォルダ名を決める
            # ------------------------------------------------

            folder_name = "New Folder"

            new_path = os.path.join(
                target_dir,
                folder_name,
            )

            number = 2

            while os.path.exists(
                new_path
            ):

                folder_name = (
                    "New Folder "
                    + str(number)
                )

                new_path = os.path.join(
                    target_dir,
                    folder_name,
                )

                number += 1

            # ------------------------------------------------
            # フォルダ作成
            # ------------------------------------------------

            try:

                os.mkdir(
                    new_path
                )

                # --------------------------------------------
                # Desktopの場合
                # --------------------------------------------

                if (
                    state["active_window"]
                    is None
                ):

                    state["desktop_icons"] = (
                        read_directory(HOME)
                    )

                    arrange_icons(
                        state["desktop_icons"],
                        width,
                        height,
                    )

                    state["desktop_selected"] = None

                    # 作成したフォルダを選択
                    for icon in state["desktop_icons"]:

                        if icon["path"] == new_path:

                            state["desktop_selected"] = (
                                icon
                            )

                            break

                # --------------------------------------------
                # Windowの場合
                # --------------------------------------------

                else:

                    window = (
                        state["active_window"]
                    )

                    window["icons"] = (
                        read_directory(
                            window["path"]
                        )
                    )

                    window_w = window["w"]

                    columns = max(
                        1,
                        (window_w - 4) // 18
                    )

                    for i, icon in enumerate(
                        window["icons"]
                    ):

                        column = i % columns
                        row = i // columns

                        icon["x"] = (
                            2
                            + column * 18
                        )

                        icon["y"] = (
                            2
                            + row * 3
                        )

                    window["selected"] = None

                    # 作成したフォルダを選択
                    for icon in window["icons"]:

                        if icon["path"] == new_path:

                            window["selected"] = (
                                icon
                            )

                            break

                state["message"] = (
                    "Created "
                    + folder_name
                )

            except OSError:

                state["message"] = (
                    "Could not create folder"
                )

            state["active_menu"] = None

            return True
        # ----------------------------------------------------
        # File → Open in Editor
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "Open in Editor"
        ):

            selected_icon = None

            # ------------------------------------------------
            # Desktopの選択
            # ------------------------------------------------

            if (
                state["desktop_selected"]
                is not None
            ):

                selected_icon = (
                    state["desktop_selected"]
                )

            # ------------------------------------------------
            # Window内の選択
            # ------------------------------------------------

            else:

                for window in state["windows"]:

                    if window["selected"] is not None:

                        selected_icon = (
                            window["selected"]
                        )

                        break

            # ------------------------------------------------
            # 選択なし
            # ------------------------------------------------

            if selected_icon is None:

                state["message"] = (
                    "No item selected"
                )

            # ------------------------------------------------
            # フォルダ
            # ------------------------------------------------

            elif selected_icon["type"] == "folder":

                state["message"] = (
                    "Cannot edit folder"
                )

            # ------------------------------------------------
            # ファイル
            # ------------------------------------------------

            else:

                edit_file(
                    state,
                    selected_icon["path"],
                )

            state["active_menu"] = None

            return True
        # ----------------------------------------------------
        # File → Get Info
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "Get Info"
        ):

            selected_icon = None

            # ------------------------------------------------
            # Desktopの選択
            # ------------------------------------------------

            if (
                state["desktop_selected"]
                is not None
            ):

                selected_icon = (
                    state["desktop_selected"]
                )

            # ------------------------------------------------
            # Window内の選択
            # ------------------------------------------------

            else:

                for window in state["windows"]:

                    if window["selected"] is not None:

                        selected_icon = (
                            window["selected"]
                        )

                        break

            # ------------------------------------------------
            # 選択なし
            # ------------------------------------------------

            if selected_icon is None:

                state["message"] = (
                    "No item selected"
                )

                state["active_menu"] = None

                return True

            # ------------------------------------------------
            # 情報を取得
            # ------------------------------------------------

            path = selected_icon["path"]

            name = os.path.basename(path)

            # ------------------------------------------------
            # 種類
            # ------------------------------------------------

            if os.path.isdir(path):

                kind = "Folder"

            else:

                extension = (
                    os.path.splitext(name)[1].lower()
                )

                kind_map = {
                    ".py": "Python Source",
                    ".sh": "Shell Script",
                    ".txt": "Text Document",
                    ".md": "Markdown Document",
                    ".jpg": "JPEG Image",
                    ".jpeg": "JPEG Image",
                    ".png": "PNG Image",
                    ".wav": "WAV Audio",
                    ".mp3": "MP3 Audio",
                    ".flac": "FLAC Audio",
                    ".ogg": "OGG Audio",
                    ".m4a": "M4A Audio",
                    ".mp4": "MP4 Video",
                    ".mkv": "MKV Video",
                    ".webm": "WebM Video",
                    ".avi": "AVI Video",
                }

                kind = kind_map.get(
                    extension,
                    "File",
                )

            # ------------------------------------------------
            # サイズ
            # ------------------------------------------------

            try:

                size = os.path.getsize(path)

                if size < 1024:

                    size_text = (
                        str(size)
                        + " bytes"
                    )

                elif size < 1024 * 1024:

                    size_text = (
                        "{:.1f} KB".format(
                            size / 1024
                        )
                    )

                elif size < 1024 * 1024 * 1024:

                    size_text = (
                        "{:.1f} MB".format(
                            size / (1024 * 1024)
                        )
                    )

                else:

                    size_text = (
                        "{:.1f} GB".format(
                            size / (1024 * 1024 * 1024)
                        )
                    )

            except OSError:

                size_text = "Unknown"

            # ------------------------------------------------
            # 更新日時
            # ------------------------------------------------

            try:

                mtime = os.path.getmtime(path)

                modified = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(mtime),
                )

            except OSError:

                modified = "Unknown"

            # ------------------------------------------------
            # Get Info状態
            # ------------------------------------------------

            state["info"] = {
                "name": name,
                "kind": kind,
                "location": os.path.dirname(path),
                "size": size_text,
                "modified": modified,
            }

            state["message"] = (
                "Get Info: "
                + name
            )

            state["active_menu"] = None

            return True


        # ----------------------------------------------------
        # File → Open
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "Open"
        ):

            selected_icon = (
                state["desktop_selected"]
            )

            # ------------------------------------------------
            # 選択されているアイコンがある
            # ------------------------------------------------

            if selected_icon is not None:

                # --------------------------------------------
                # フォルダなら開く
                # --------------------------------------------

                if selected_icon["type"] == "folder":

                    new_window = create_window(
                        selected_icon["path"],
                        len(
                            state["windows"]
                        ) + 1,
                        width,
                        height,
                    )

                    state["windows"].append(
                        new_window
                    )

                    state["active_window"] = (
                        new_window
                    )

                    state["message"] = (
                        "Opened "
                        + selected_icon["name"]
                    )

                # --------------------------------------------
                # ファイルなら起動
                # --------------------------------------------

                else:

                    launch_file(
                        state,
                        selected_icon["path"]
                )
                
            else:

                state["message"] = (
                    "No item selected"
                )

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # File → Quit
        # ----------------------------------------------------

        if (
            menu_name == "File"
            and
            item == "Quit"
        ):

            state["active_menu"] = None

            state["message"] = (
                "Goodbye"
            )

            state["running"] = False

            return True

        # ----------------------------------------------------
        # Edit → Copy
        # ----------------------------------------------------

        if (
            menu_name == "Edit"
            and
            item == "Copy"
        ):

            selected_icon = None

            # -----------------------------------------------
            # ウィンドウ内の選択
            # -----------------------------------------------

            active_window = state.get(
                "active_window"
            )

            if active_window is not None:

                selected_icon = (
                    active_window.get("selected")
                )

            # -----------------------------------------------
            # ウィンドウに選択がなければ
            # デスクトップの選択を見る
            # -----------------------------------------------

            if selected_icon is None:

                selected_icon = (
                    state["desktop_selected"]
                )

            # -----------------------------------------------
            # Copy
            # -----------------------------------------------

            if selected_icon is not None:

                state["clipboard"] = {
                    "icon": selected_icon,
                    "action": "copy",
                }

                state["message"] = (
                    "Copied "
                    + selected_icon["name"]
                )

            else:

                state["message"] = (
                    "No item selected"
                )

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # Edit → Cut
        # ----------------------------------------------------

        if (
            menu_name == "Edit"
            and
            item == "Cut"
        ):

            selected_icon = None

            # -----------------------------------------------
            # ウィンドウ内の選択
            # -----------------------------------------------

            active_window = state.get(
                "active_window"
            )

            if active_window is not None:

                selected_icon = (
                    active_window.get("selected")
                )

            # -----------------------------------------------
            # ウィンドウに選択がなければ
            # デスクトップの選択を見る
            # -----------------------------------------------

            if selected_icon is None:

                selected_icon = (
                    state["desktop_selected"]
                )

            # -----------------------------------------------
            # Cut
            # -----------------------------------------------

            if selected_icon is not None:

                state["clipboard"] = {
                    "icon": selected_icon,
                    "action": "cut",
                }

                state["message"] = (
                    "Cut "
                    + selected_icon["name"]
                )

            else:

                state["message"] = (
                    "No item selected"
                )

            state["active_menu"] = None

            return True


        # ----------------------------------------------------
        # Edit → Clear
        # ----------------------------------------------------

        if (
            menu_name == "Edit"
            and
            item == "Clear"
        ):

            selected_icon = None
            source_window = None

            # -----------------------------------------------
            # ウィンドウ内の選択
            # -----------------------------------------------

            active_window = state.get(
                "active_window"
            )

            if active_window is not None:

                # -------------------------------------------
                # Trashの中ではClearしない
                # -------------------------------------------

                if (
                    active_window["path"]
                    != TRASH_PATH
                ):

                    selected_icon = (
                        active_window.get(
                            "selected"
                        )
                    )

                    if selected_icon is not None:

                        source_window = (
                            active_window
                        )

            # -----------------------------------------------
            # ウィンドウに選択がなければ
            # デスクトップの選択を見る
            # -----------------------------------------------

            if selected_icon is None:

                selected_icon = (
                    state["desktop_selected"]
                )

                source_window = None

            # -----------------------------------------------
            # 選択されていない
            # -----------------------------------------------

            if selected_icon is None:

                state["message"] = (
                    "No item selected"
                )

                state["active_menu"] = None

                return True

            # -----------------------------------------------
            # Trashへ移動
            # -----------------------------------------------

            name = selected_icon["name"]
            source = selected_icon["path"]

            if move_to_trash(source):

                # -------------------------------------------
                # Undo情報を保存
                # -------------------------------------------

                state["undo"] = {
                    "action": "move_to_trash",
                    "name": name,
                }
                # -------------------------------------------
                # デスクトップを更新
                # -------------------------------------------

                state["desktop_icons"] = (
                    read_directory(HOME)
                )

                arrange_icons(
                    state["desktop_icons"],
                    width,
                    height,
                )

                state["desktop_selected"] = None

                # -------------------------------------------
                # 元のウィンドウを更新
                # -------------------------------------------

                if source_window is not None:

                    source_window["icons"] = (
                        read_directory(
                            source_window["path"]
                        )
                    )

                    window_w = (
                        source_window["w"]
                    )

                    columns = max(
                        1,
                        (window_w - 4) // 18
                    )

                    for i, icon in enumerate(
                        source_window["icons"]
                    ):

                        column = i % columns
                        row = i // columns

                        icon["x"] = (
                            2
                            + column * 18
                        )

                        icon["y"] = (
                            2
                            + row * 3
                        )

                    source_window["selected"] = None

                state["message"] = (
                    "Moved to Trash: "
                    + name
                )

            else:

                state["message"] = (
                    "Could not move to Trash: "
                    + name
                )

            state["active_menu"] = None

            return True
        # ----------------------------------------------------
        # Edit → Rename
        # ----------------------------------------------------

        if (
            menu_name == "Edit"
            and
            item == "Rename"
        ):

            target = None

            # ------------------------------------------------
            # デスクトップの選択
            # ------------------------------------------------

            if state["desktop_selected"] is not None:

                target = state["desktop_selected"]

            # ------------------------------------------------
            # ウィンドウ内の選択
            # ------------------------------------------------

            else:

                for window in state["windows"]:

                    if window["selected"] is not None:

                        target = window["selected"]
                        break

            # ------------------------------------------------
            # 選択されていない
            # ------------------------------------------------

            if target is None:

                state["message"] = (
                    "No item selected"
                )

                state["active_menu"] = None

                return True

            # ------------------------------------------------
            # Rename情報を保存
            # ------------------------------------------------

            state["rename"] = {
                "path": target["path"],
                "old_name": target["name"],
                "name": target["name"],
                "cursor": len(target["name"]),
            }
          

            state["message"] = (
                "Rename: "
                + target["name"]
            )

            state["active_menu"] = None

            return True
        
        # ----------------------------------------------------
        # Edit → Undo
        # ----------------------------------------------------

        if (
            menu_name == "Edit"
            and
            item == "Undo"
        ):
        

            undo = state.get(
                "undo"
            )
           
        
            

            if undo is None:

                state["message"] = (
                    "Nothing to undo"
                )

                state["active_menu"] = None

                return True

            if undo.get("action") == "move_to_trash":

                name = undo.get(
                    "name"
                )

                if restore_from_trash(name):

                    # ---------------------------------------
                    # デスクトップ更新
                    # ---------------------------------------

                    state["desktop_icons"] = (
                        read_directory(HOME)
                    )

                    arrange_icons(
                        state["desktop_icons"],
                        width,
                        height,
                    )

                    state["desktop_selected"] = None

                    # ---------------------------------------
                    # 開いているウィンドウを更新
                    # ---------------------------------------

                    for window in state["windows"]:

                        window["icons"] = (
                            read_directory(
                                window["path"]
                            )
                        )

                        window_w = window["w"]

                        columns = max(
                            1,
                            (window_w - 4) // 18
                        )

                        for i, icon in enumerate(
                            window["icons"]
                        ):

                            column = i % columns
                            row = i // columns

                            icon["x"] = (
                                2
                                + column * 18
                            )

                            icon["y"] = (
                                2
                                + row * 3
                            )

                        window["selected"] = None

                    state["undo"] = None

                    state["message"] = (
                        "Undo: "
                        + name
                    )

            elif undo.get("action") == "move":

          
                    source = undo.get(
                        "source"
                    )

                    destination = undo.get(
                        "destination"
                    )

                    name = undo.get(
                        "name"
                    )
           


                    try:

                        if (
                            source
                            and destination
                            and os.path.exists(source)
                        ):

                            shutil.move(
                                source,
                                destination,
                            )

                            # ---------------------------------------
                            # デスクトップ更新
                            # ---------------------------------------

                            state["desktop_icons"] = (
                                read_directory(HOME)
                            )

                            arrange_icons(
                                state["desktop_icons"],
                                width,
                                height,
                            )

                            state["desktop_selected"] = None

                            # ---------------------------------------
                            # 開いているウィンドウを更新
                            # ---------------------------------------

                            for window in state["windows"]:

                                window["icons"] = (
                                    read_directory(
                                        window["path"]
                                    )
                                )

                                window_w = window["w"]

                                columns = max(
                                    1,
                                    (window_w - 4) // 18
                                )

                                for i, icon in enumerate(
                                    window["icons"]
                                ):

                                    column = i % columns
                                    row = i // columns

                                    icon["x"] = (
                                        2
                                        + column * 18
                                    )

                                    icon["y"] = (
                                        2
                                        + row * 3
                                    )

                                window["selected"] = None

                            state["undo"] = None

                            state["message"] = (
                                "Undo: "
                                + name
                            )

                        else:

                            state["message"] = (
                                "Could not undo"
                            )

                    except OSError:

                        state["message"] = (
                            "Could not undo"
                        )
            elif undo.get("action") == "rename":

                source = undo.get(
                    "source"
                )

                destination = undo.get(
                    "destination"
                )

                name = undo.get(
                    "name"
                )

                old_name = undo.get(
                    "old_name"
                )

                try:

                    if (
                        source
                        and destination
                        and os.path.exists(source)
                    ):

                        os.rename(
                            source,
                            destination,
                        )
                    # ------------------------------------------------
                    # Rename Undoによるウィンドウ更新
                    # ------------------------------------------------

                        source_abs = os.path.abspath(
                            source
                        )

                        destination_abs = os.path.abspath(
                            destination
                        )

                        for window in state["windows"]:

                            window_path = os.path.abspath(
                                window["path"]
                            )

                        # --------------------------------------------
                        # Renameしたフォルダ自身
                        # --------------------------------------------

                            if window_path == source_abs:

                                window["path"] = (
                                    destination_abs
                                )

                        # --------------------------------------------
                        # Renameしたフォルダの中にあるウィンドウ
                        # --------------------------------------------

                            elif window_path.startswith(
                                source_abs + os.sep
                            ):

                                relative = os.path.relpath(
                                    window_path,
                                    source_abs,
                                )

                                window["path"] = (
                                    os.path.join(
                                        destination_abs,
                                        relative,
                                    )
                                )
                    # ------------------------------------------------
                    # デスクトップ更新
                    # ------------------------------------------------

                        state["desktop_icons"] = (
                            read_directory(HOME)
                        )

                        arrange_icons(
                            state["desktop_icons"],
                            width,
                            height,
                        )

                        state["desktop_selected"] = None

                    # ------------------------------------------------
                    # ウィンドウ更新
                    # ------------------------------------------------

                        for window in state["windows"]:

                            window["icons"] = (
                                read_directory(
                                    window["path"]
                                )
                            )

                            window_w = window["w"]

                            columns = max(
                                1,
                                (window_w - 4) // 18
                            )

                            for i, icon in enumerate(
                                window["icons"]
                            ):

                                column = i % columns
                                row = i // columns

                                icon["x"] = (
                                    2
                                    + column * 18
                                )

                                icon["y"] = (
                                    2
                                    + row * 3
                                )

                            window["selected"] = None

                        state["undo"] = None

                        state["message"] = (
                            "Undo: "
                            + old_name
                        )

                    else:

                        state["message"] = (
                            "Could not undo"
                        )

                except OSError:

                    state["message"] = (
                        "Could not undo"
                    )        
            else:

                state["message"] = (
                    "Could not undo"
                )

                

            state["active_menu"] = None

            return True
        # ----------------------------------------------------
        # Edit → Paste
        # ----------------------------------------------------

        if (
            menu_name == "Edit"
            and
            item == "Paste"
        ):

            clipboard = state.get(
                "clipboard"
            )

            if clipboard is None:

                state["message"] = (
                    "Nothing to paste"
                )

                state["active_menu"] = None

                return True

            clipboard_icon = clipboard.get(
                "icon"
            )

            action = clipboard.get(
                "action"
            )
  
            if clipboard_icon is None:

                state["message"] = (
                    "Nothing to paste"
                )

                state["clipboard"] = None
                state["active_menu"] = None

                return True

            source = clipboard_icon.get(
                "path"
            )

            if not source or not os.path.exists(source):

                state["message"] = (
                    "Source no longer exists"
                )

                state["clipboard"] = None
                state["active_menu"] = None

                return True

            # -----------------------------------------------
            # 元ファイルの場所を記録
            # -----------------------------------------------

            source_dir = os.path.dirname(
                source
            )

            # -----------------------------------------------
            # Paste先を決定
            # -----------------------------------------------

            active_window = state.get(
                "active_window"
            )

            if active_window is not None:

                destination_dir = (
                    active_window["path"]
                )

            else:

                destination_dir = HOME

            # -----------------------------------------------
            # 同名ファイルがある場合
            # -----------------------------------------------

            original_name = os.path.basename(
                source
            )

            name, extension = os.path.splitext(
                original_name
            )

            destination = os.path.join(
                destination_dir,
                original_name,
            )

            number = 2

            while os.path.exists(destination):

                if extension:

                    new_name = (
                        name
                        + " copy "
                        + str(number)
                        + extension
                    )

                else:

                    new_name = (
                        name
                        + " copy "
                        + str(number)
                    )

                destination = os.path.join(
                    destination_dir,
                    new_name,
                )

                number += 1

            # -----------------------------------------------
            # Copy / Cut
            # -----------------------------------------------

            try:

                if action == "cut":

                    shutil.move(
                        source,
                        destination,
                    )
                    state["undo"] = {
                        "action": "move",
                        "source": destination,
                        "destination": source,
                        "name": os.path.basename(destination),
                    }
          
                else:

                    if os.path.isdir(source):

                        shutil.copytree(
                            source,
                            destination,
                        )

                    else:

                        shutil.copy2(
                            source,
                            destination,
                        )

            except OSError:

                state["message"] = (
                    "Could not paste"
                )

                state["active_menu"] = None

                return True

            # -----------------------------------------------
            # デスクトップを更新
            # -----------------------------------------------

            state["desktop_icons"] = (
                read_directory(HOME)
            )

            arrange_icons(
                state["desktop_icons"],
                width,
                height,
            )

            # -----------------------------------------------
            # 開いている全ウィンドウを更新
            # -----------------------------------------------

            for window in state["windows"]:

                window_path = os.path.abspath(
                    window["path"]
                )

                source_path = os.path.abspath(
                    source_dir
                )

                destination_path = os.path.abspath(
                    destination_dir
                )

                if (
                    window_path == source_path
                    or
                    window_path == destination_path
                ):

                    window["icons"] = (
                        read_directory(
                            window["path"]
                        )
                    )

                    # create_window() と同じ考え方で
                    # アイコンを並べ直す

                    window_w = window["w"]

                    columns = max(
                        1,
                        (window_w - 4) // 18
                    )

                    for i, icon in enumerate(
                        window["icons"]
                    ):

                        column = i % columns
                        row = i // columns

                        icon["x"] = (
                            2
                            + column * 18
                        )

                        icon["y"] = (
                            2
                            + row * 3
                        )

                    window["selected"] = None

            # -----------------------------------------------
            # Clipboardを消去
            # -----------------------------------------------

            state["clipboard"] = None

            state["desktop_selected"] = None

            if action != "cut":

                state["message"] = (
                    "Pasted "
                    + os.path.basename(destination)
                )

            state["active_menu"] = None
           

            return True
  
        # ----------------------------------------------------
        # View → Clean Up
        # ----------------------------------------------------

        if (
            menu_name == "View"
            and
            item == "Clean Up"
        ):

            arrange_icons(
                state["desktop_icons"],
                width,
                height,
            )

            state["desktop_selected"] = None

            state["message"] = (
                "Cleaned Up"
            )

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # View → by Name
        # ----------------------------------------------------

        if (
            menu_name == "View"
            and
            item == "by Name"
        ):

            state["desktop_icons"].sort(
                key=lambda icon: (
                    icon["type"] != "folder",
                    icon["name"].lower(),
                )
            )

            arrange_icons(
                state["desktop_icons"],
                width,
                height,
            )

            state["desktop_selected"] = None

            state["message"] = (
                "Sorted by Name"
            )

            state["active_menu"] = None

            return True


        # ----------------------------------------------------
        # View → by Date
        # ----------------------------------------------------

        if (
            menu_name == "View"
            and
            item == "by Date"
        ):

            def modification_time(icon):

                try:
                    return os.path.getmtime(
                        icon["path"]
                    )

                except (
                    FileNotFoundError,
                    PermissionError,
                    OSError,
                ):
                    return 0

            state["desktop_icons"].sort(
                key=lambda icon: (
                    icon["type"] != "folder",
                    -modification_time(icon),
                )
            )

            arrange_icons(
                state["desktop_icons"],
                width,
                height,
            )

            state["desktop_selected"] = None

            state["message"] = (
                "Sorted by Date"
            )

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # View → by Icon
        # ----------------------------------------------------

        if (
            menu_name == "View"
            and
            item == "by Icon"
        ):

            state["desktop_icons"].sort(
                key=lambda icon: (
                    icon["type"] != "folder",
                    icon["name"].lower(),
                )
            )

            arrange_icons(
                state["desktop_icons"],
                width,
                height,
            )

            state["desktop_selected"] = None

            state["message"] = (
                "Arranged by Icon"
            )

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # Special → Restart
        # ----------------------------------------------------

        if (
            menu_name == "Special"
            and
            item == "Restart"
        ):

            state["dialog"] = {
                "type": "confirm",
                "message": (
                    "Are you sure you want to restart?"
                ),
                "action": "restart",
            }

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # Special → Shut Down
        # ----------------------------------------------------

        if (
            menu_name == "Special"
            and
            item == "Shut Down"
        ):

            state["dialog"] = {
                "type": "confirm",
                "message": (
                    "Are you sure you want to shut down?"
                ),
                "action": "shutdown",
            }

            state["active_menu"] = None

            return True


        # ----------------------------------------------------
        # Special → Empty Trash
        # ----------------------------------------------------

        if (
            menu_name == "Special"
            and
            item == "Empty Trash"
        ):

            state["dialog"] = {
                "type": "confirm", 
                "message": ( 
                    "Are you sure you want to empty the Trash?" 
                    ), 
                    "action": "empty_trash", 
            } 
            
            state["active_menu"] = None 
            
            return True

            if empty_trash():

                # ------------------------------------------------
                # 開いているTrashウィンドウを更新
                # ------------------------------------------------

                for window in state["windows"]:

                    if window["path"] == TRASH_PATH:

                        window["icons"] = read_directory(
                            TRASH_PATH
                        )

                        window["selected"] = None

                state["message"] = (
                    "Trash emptied"
                )

            else:

                state["message"] = (
                    "Could not empty Trash"
                )

            state["active_menu"] = None

            return True

        # ----------------------------------------------------
        # その他のメニュー項目
        # ----------------------------------------------------

        state["active_menu"] = None

        return True

    return False

# ============================================================
# マウスイベント
# ============================================================

def handle_mouse_event(
    stdscr,
    state,
):

    try:

        (
            _,
            mx,
            my,
            _,
            mouse_state,
        ) = curses.getmouse()

    
 
    except curses.error:

        return
 
    height, width = (
        stdscr.getmaxyx()
    )

    update_mouse_position(
        state,
        width,
        height,
        mx,
        my,
    )

    mouse_x = state["mouse_x"]
    mouse_y = state["mouse_y"]

   
    
    # ========================================================
    # マウスホイール
    # ========================================================

    if mouse_state & curses.BUTTON4_PRESSED:

        window = window_at(
            state["windows"],
            mouse_x,
            mouse_y,
        )

        if window is not None:

            scroll_window(
                window,
                -3,
            )

        return


    if mouse_state & curses.BUTTON5_PRESSED:

        window = window_at(
            state["windows"],
            mouse_x,
            mouse_y,
        )

        if window is not None:

            scroll_window(
                window,
                3,
            )

        return

    # ========================================================
    # 確認ダイアログ
    # ========================================================

    if state["dialog"] is not None:

        if mouse_state & curses.BUTTON1_PRESSED:

            height, width = (
                stdscr.getmaxyx()
            )

            dialog_w = max(
                40,
                len(
                    state["dialog"]["message"]
                ) + 8,
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

            # ------------------------------------------------
            # Yes
            # ------------------------------------------------

            yes_text = "[ Yes ]"

            yes_x = (
                dialog_x
                + (
                    dialog_w
                    - len(
                        "[ Yes ]    [ No ]"
                    )
                ) // 2
            )

            no_x = (
                yes_x
                + len("[ Yes ]")
                + 4
            )

            if (
                dialog_y + 4 == mouse_y
                and
                yes_x <= mouse_x
                < yes_x + len(yes_text)
            ):

                action = state["dialog"].get(
                    "action"
                )

                state["dialog"] = None

                if action == "restart":

                    subprocess.Popen(
                        [
                             "tmux",
                            "new-window",
                            "sudo reboot"
                            
                        ]
                    )

                    return                
                
                if action == "shutdown":

                    subprocess.Popen(
                        [
                             "tmux",
                            "new-window",
                            "sudo poweroff"
                            
                        ]
                    )

                    return
                    
                if action == "empty_trash":

                    if empty_trash():

                        for window in state["windows"]:

                            if (
                                window["path"]
                                == TRASH_PATH
                            ):

                                window["icons"] = (
                                    read_directory(
                                        TRASH_PATH
                                    )
                                )

                                window["selected"] = (
                                    None
                                )

                        state["message"] = (
                            "Trash emptied"
                        )

                    else:

                        state["message"] = (
                            "Could not empty Trash"
                        )

                return

            # ------------------------------------------------
            # No
            # ------------------------------------------------

            if (
                dialog_y + 4 == mouse_y
                and
                no_x <= mouse_x
                < no_x + len("[ No ]")
            ):

                state["dialog"] = None

                state["message"] = (
                    "Cancelled"
                )

                return

        return

    # --------------------------------------------------------
    # ウィンドウ内アイコンのドラッグ
    # --------------------------------------------------------

    if state["window_icon_dragging"] is not None:

        drag = state["window_icon_dragging"]

        drag_window = drag["window"]
        drag_icon = drag["icon"]

        # ----------------------------------------------------
        # 元のウィンドウの外へ出たか確認
        # ----------------------------------------------------

        inside_source_window = point_in_window(
            drag_window,
            mouse_x,
            mouse_y,
        )

        # ----------------------------------------------------
        # ウィンドウの外へ出たら
        # 「ウィンドウ内移動」から
        # 「ファイル・フォルダ移動」へ切り替える
        # ----------------------------------------------------

        if not inside_source_window:

            state["dragging_item"] = drag_icon
            state["dragging_item_window"] = drag_window

            state["window_icon_dragging"] = None
            state["window_icon_drag_offset_x"] = 0
            state["window_icon_drag_offset_y"] = 0

            state["message"] = (
                "Move: "
                + drag_icon["name"]
            )

            # ------------------------------------------------
            # そのまま外へドラッグしているので、
            # ボタンを離した瞬間に移動処理へ進ませる
            # ------------------------------------------------

            if mouse_state == curses.BUTTON1_RELEASED:

                drop_item_on_folder(
                    state,
                    width,
                    height,
                )

                state["dragging_item"] = None
                state["dragging_item_window"] = None

            return

        # ----------------------------------------------------
        # まだ元のウィンドウ内なら
        # 通常のアイコン移動
        # ----------------------------------------------------

        update_window_icon_drag(
            state,
        )

        if mouse_state & curses.BUTTON1_RELEASED:

            state["window_icon_dragging"] = None
            state["window_icon_drag_offset_x"] = 0
            state["window_icon_drag_offset_y"] = 0

        return

    # ========================================================
    # ファイル・フォルダをドラッグ中
    # ========================================================

    if state["dragging_item"] is not None:

        if mouse_state & curses.BUTTON1_RELEASED:

            drop_item_on_folder(
                state,
                width, 
                height,                               
            )

            state["dragging_item"] = None
            state["dragging_item_window"] = None

        return



    # ========================================================
    # デスクトップアイコンをドラッグ中
    # ========================================================
    #
    # 通常のクリック判定より先に処理する。
    # これにより Trash の上へ移動しても
    # ドラッグが途中で途切れない。
    #

    if state["desktop_dragging"] is not None:

        update_desktop_drag(
            state,
            width,
            height,
        )

        if mouse_state & curses.BUTTON1_RELEASED:

            drop_desktop_icon(
                state,
                width,
                height,
            )

            state["desktop_dragging"] = None

        return

    # ========================================================
    # ウィンドウ移動中
    # ========================================================

    if state["dragging_window"] is not None:

        update_window_drag(
            state,
            width,
            height,
        )

        if mouse_state & curses.BUTTON1_RELEASED:

            state["dragging_window"] = None

        return

    # ========================================================
    # ウィンドウリサイズ中
    # ========================================================

    if state["resizing_window"] is not None:

        update_resize(
            state,
            width,
            height,
        )

        if mouse_state & curses.BUTTON1_RELEASED:

            state["resizing_window"] = None

        return

    # ========================================================
    # マウスボタン押下
    # ========================================================

    if mouse_state & curses.BUTTON1_PRESSED:

        # ----------------------------------------------------
        # メニュー
        # ----------------------------------------------------

        if handle_menu_click(
            state,
            mouse_x,
            mouse_y,
            width, 
            height,
        ):

            return

        # ----------------------------------------------------
        # Trashクリック
        # ----------------------------------------------------

        if point_in_trash(
            width,
            height,
            mouse_x,
            mouse_y,
        ):

            state["trash_selected"] = True
            state["active_window"] = None

            if is_double_click(
                state,
                state["trash_item"],
            ):

                new_window = create_window(
                    TRASH_PATH,
                    len(
                        state["windows"]
                    ) + 1,
                    width,
                    height,
                )

                state["windows"].append(
                    new_window
                )

                state["active_window"] = (
                    get_active_window(
                        state["windows"]
                    )
                )

                state["trash_selected"] = False

                state["message"] = (
                    "Opened: Trash"
                )

            return

        # ----------------------------------------------------
        # ウィンドウ
        # ----------------------------------------------------

        window = window_at(
            state["windows"],
            mouse_x,
            mouse_y,
        )

        if window is not None:
         
            handle_window_click(
                state,
                window,
                mouse_x,
                mouse_y,
                width,
                height,
            )

            return

        # ----------------------------------------------------
        # デスクトップ
        # ----------------------------------------------------

        handle_desktop_click(
            state,
            mouse_x,
            mouse_y,
            width,
            height,
        )

        return

    # ========================================================
    # マウスボタン離す
    # ========================================================

    if mouse_state == curses.BUTTON1_RELEASED:

        state["desktop_dragging"] = None

        state["dragging_window"] = None

        state["resizing_window"] = None

        state["window_icon_press"] = None
# ============================================================
# メインイベント
# ============================================================

def handle_event(
    stdscr,
    key,
    state,
):
    # ========================================================
    # Get Info ダイアログ
    # ========================================================

    if state["info"] is not None:

        # Enter / Esc で閉じる
        if key in (
            curses.KEY_ENTER,
            10,
            13,
            27,
        ):

            state["info"] = None

            state["message"] = (
                "Get Info closed"
            )

        return
    # ========================================================
    # Rename入力
    # ========================================================

    if state["rename"] is not None:

        rename = state["rename"]

        # ----------------------------------------------------
        # Enter → 確定
        # ----------------------------------------------------

        if key in (
            curses.KEY_ENTER,
            10,
            13,
        ):

            new_name = rename["name"]

            if new_name == "":

                state["message"] = (
                    "Name cannot be empty"
                )

                return

            if "/" in new_name:

                state["message"] = (
                    "Invalid name"
                )

                return

            if new_name in (
                ".",
                "..",
            ):

                state["message"] = (
                    "Invalid name"
                )

                return

            old_path = rename["path"]

            old_name = rename["old_name"]

            new_path = os.path.join(
                os.path.dirname(old_path),
                new_name,
            )

            if (
                new_path != old_path
                and
                os.path.exists(new_path)
            ):

                state["message"] = (
                    "Already exists"
                )

                return

            try:

                # ------------------------------------------------
                # 実際に名前を変更
                # ------------------------------------------------

                os.rename(
                    old_path,
                    new_path,
                )
                # ------------------------------------------------
                # Renameしたフォルダを開いているウィンドウを更新
                # ------------------------------------------------

                old_abs = os.path.abspath(
                    old_path
                )

                new_abs = os.path.abspath(
                    new_path
                )

                for window in state["windows"]:

                    window_path = os.path.abspath(
                        window["path"]
                    )

                    # --------------------------------------------
                    # Renameしたフォルダ自身
                    # --------------------------------------------

                    if window_path == old_abs:

                        window["path"] = new_abs

                    # --------------------------------------------
                    # Renameしたフォルダの中にあるウィンドウ
                    # --------------------------------------------

                    elif window_path.startswith(
                        old_abs + os.sep
                    ):

                        relative = os.path.relpath(
                            window_path,
                            old_abs,
                        )

                        window["path"] = os.path.join(
                            new_abs,
                            relative,
                        )
                # ------------------------------------------------
                # Undo情報を保存
                # ------------------------------------------------

                state["undo"] = {
                    "action": "rename",
                    "source": new_path,
                    "destination": old_path,
                    "name": new_name,
                    "old_name": old_name,
                }
                
                # ------------------------------------------------
                # デスクトップ更新
                # ------------------------------------------------

                height, width = (
                    stdscr.getmaxyx()
                )

                state["desktop_icons"] = (
                    read_directory(HOME)
                )

                arrange_icons(
                    state["desktop_icons"],
                    width,
                    height,
                )

                state["desktop_selected"] = None

                # ------------------------------------------------
                # 開いているウィンドウを更新
                # ------------------------------------------------

                for window in state["windows"]:

                    window["icons"] = (
                        read_directory(
                            window["path"]
                        )
                    )

                    window_w = window["w"]

                    columns = max(
                        1,
                        (window_w - 4) // 18
                    )

                    for i, icon in enumerate(
                        window["icons"]
                    ):

                        column = i % columns
                        row = i // columns

                        icon["x"] = (
                            2
                            + column * 18
                        )

                        icon["y"] = (
                            2
                            + row * 3
                        )

                    window["selected"] = None

                # ------------------------------------------------
                # Rename終了
                # ------------------------------------------------

                state["rename"] = None

                state["message"] = (
                    "Renamed: "
                    + new_name
                )

            except OSError:

                state["message"] = (
                    "Could not rename"
                )

            return


        # ----------------------------------------------------
        # Esc → キャンセル
        # ----------------------------------------------------

        if key == 27:

            state["rename"] = None

            state["message"] = (
                "Rename cancelled"
            )

            return

        # ----------------------------------------------------
        # Backspace
        # ----------------------------------------------------

        if key in (
            curses.KEY_BACKSPACE,
            127,
            8,
        ):

            cursor = rename["cursor"]

            if cursor > 0:

                name = rename["name"]

                rename["name"] = (
                    name[:cursor - 1]
                    +
                    name[cursor:]
                )

                rename["cursor"] -= 1

            return

        # ----------------------------------------------------
        # 通常文字
        # ----------------------------------------------------

        if 32 <= key <= 126:

            cursor = rename["cursor"]

            name = rename["name"]

            rename["name"] = (
                name[:cursor]
                +
                chr(key)
                +
                name[cursor:]
            )

            rename["cursor"] += 1

            return

        return
        
    if key in (
        ord("q"),
        ord("Q"),
    ):

        state["running"] = False

        return

    if key == 27:

        handle_escape(
            state,
        )

        return

    if key == curses.KEY_MOUSE:

        handle_mouse_event(
            stdscr,
            state,
        )



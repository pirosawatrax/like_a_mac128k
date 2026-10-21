# ============================================================
# filesystem.py
# ファイルシステム操作
# ============================================================

import os

from constants import (
    HOME,
    TRASH_PATH,
    HIDE_DOTFILES,
    DESKTOP_MARGIN_X,
    DESKTOP_MARGIN_Y,
    DESKTOP_COLUMN_WIDTH,
    DESKTOP_ROW_HEIGHT,
    FILE_SYMBOL,
    DIR_SYMBOL,
)

_show_hidden = not HIDE_DOTFILES


def set_show_hidden(value):
    global _show_hidden
    _show_hidden = bool(value)


def show_hidden_enabled():
    return _show_hidden


# ============================================================
# パス判定
# ============================================================

def same_path(a, b):
    return os.path.abspath(a) == os.path.abspath(b)


def is_inside(path, parent):
    """path が parent の内側にあるか (同一は False)"""

    path = os.path.abspath(path)
    parent = os.path.abspath(parent)

    if path == parent:
        return False

    try:
        return os.path.commonpath([path, parent]) == parent
    except ValueError:
        return False


def unique_destination(directory, name):
    """
    directory 内で重複しないパスを返す。
    重複する場合は "name copy 2.ext" 形式にする。
    """

    destination = os.path.join(directory, name)

    if not os.path.lexists(destination):
        return destination

    base, extension = os.path.splitext(name)
    number = 2

    while True:

        candidate = os.path.join(
            directory,
            "{} copy {}{}".format(base, number, extension),
        )

        if not os.path.lexists(candidate):
            return candidate

        number += 1


# ============================================================
# アイコン作成
# ============================================================

def printable(text):
    """制御文字を ? に置き換える (画面が壊れるのを防ぐ)"""

    return "".join(c if c.isprintable() else "?" for c in text)


def make_icon(path, is_dir=None):

    name = os.path.basename(path)

    if is_dir is None:
        is_dir = os.path.isdir(path)

    return {
        "name": name,
        "label": printable(name),
        "path": path,
        "symbol": DIR_SYMBOL if is_dir else FILE_SYMBOL,
        "type": "folder" if is_dir else "file",
        "x": 0,
        "y": 0,
    }


# ============================================================
# ディレクトリ読み込み (scandir: stat 回数が少なく Pi Zero 向け)
# ============================================================

def read_directory(path):

    show_hidden = _show_hidden or same_path(path, TRASH_PATH)

    try:
        with os.scandir(path) as it:
            entries = list(it)
    except OSError:
        return []

    icons = []

    for entry in entries:

        if not show_hidden and entry.name.startswith("."):
            continue

        try:
            is_dir = entry.is_dir()
        except OSError:
            is_dir = False

        icons.append(make_icon(entry.path, is_dir))

    icons.sort(
        key=lambda icon: (
            icon["type"] != "folder",
            icon["name"].lower(),
        )
    )

    return icons


# ============================================================
# デスクトップ配置
# ============================================================

def desktop_columns(width):
    return max(1, (width - 8) // DESKTOP_COLUMN_WIDTH)


def grid_position(index, width):

    columns = desktop_columns(width)

    return (
        DESKTOP_MARGIN_X + (index % columns) * DESKTOP_COLUMN_WIDTH,
        DESKTOP_MARGIN_Y + (index // columns) * DESKTOP_ROW_HEIGHT,
    )


def arrange_icons(icons, width, height=None):
    """全アイコンをグリッドに並べ直す (画面外はスクロールで見る)"""

    for i, icon in enumerate(icons):
        icon["x"], icon["y"] = grid_position(i, width)


def refresh_desktop_icons(old_icons, width):
    """
    HOME を読み直す。
    既存アイコンは位置を保持し、新しいものは空きマスに置く。
    """

    new_icons = read_directory(HOME)

    old_positions = {
        icon["path"]: (icon["x"], icon["y"])
        for icon in old_icons
    }

    occupied = set()

    for icon in new_icons:

        pos = old_positions.get(icon["path"])

        if pos is not None:
            icon["x"], icon["y"] = pos
            occupied.add(pos)

    index = 0

    for icon in new_icons:

        if icon["path"] in old_positions:
            continue

        while grid_position(index, width) in occupied:
            index += 1

        pos = grid_position(index, width)
        icon["x"], icon["y"] = pos
        occupied.add(pos)

    return new_icons


# ============================================================
# ヒットテスト (ウィンドウ内ローカル座標用)
# ============================================================

def icon_at(icons, x, y, label_width, exclude=None):

    for icon in reversed(icons):

        if icon is exclude:
            continue

        if (
            icon["x"] <= x < icon["x"] + label_width
            and icon["y"] <= y <= icon["y"] + 1
        ):
            return icon

    return None

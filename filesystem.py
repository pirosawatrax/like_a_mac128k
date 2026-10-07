# ============================================================
# filesystem.py
# ファイルシステム操作
# ============================================================

import os

from constants import (
    DESKTOP_MARGIN_X,
    DESKTOP_MARGIN_Y,
    DESKTOP_COLUMN_WIDTH,
    DESKTOP_ROW_HEIGHT,
    FILE_SYMBOL,
    DIR_SYMBOL,
)


# ============================================================
# アイコン作成
# ============================================================

def make_icon(path):
    """
    ファイルまたはディレクトリから
    Finder用アイコン情報を生成
    """

    name = os.path.basename(path)

    if os.path.isdir(path):
        symbol = DIR_SYMBOL
        file_type = "folder"
    else:
        symbol = FILE_SYMBOL
        file_type = "file"

    return {
        "name": name,
        "path": path,
        "symbol": symbol,
        "type": file_type,
        "x": 5,
        "y": 5,
    }


# ============================================================
# ディレクトリ読み込み
# ============================================================

def read_directory(path):
    """
    ディレクトリ内容を取得
    ディレクトリを先頭に並べる
    """

    icons = []

    try:

        names = sorted(
            os.listdir(path),
            key=lambda name: (
                not os.path.isdir(
                    os.path.join(path, name)
                ),
                name.lower(),
            ),
        )

        for name in names:

            full_path = os.path.join(
                path,
                name,
            )

            try:
                icons.append(
                    make_icon(full_path)
                )

            except OSError:
                pass

    except PermissionError:
        pass

    except OSError:
        pass

    return icons


# ============================================================
# デスクトップアイコン配置
# ============================================================

def arrange_icons(
    icons,
    width,
    height,
):
    """
    デスクトップ上へ自動配置
    """

    max_columns = max(
        1,
        (width - 8)
        // DESKTOP_COLUMN_WIDTH
    )

    for i, icon in enumerate(icons):

        column = i % max_columns
        row = i // max_columns

        icon["x"] = (
            DESKTOP_MARGIN_X
            + column
            * DESKTOP_COLUMN_WIDTH
        )

        icon["y"] = (
            DESKTOP_MARGIN_Y
            + row
            * DESKTOP_ROW_HEIGHT
        )

        if icon["y"] >= height - 4:
            icon["y"] = height - 5


# ============================================================
# アイコンヒットテスト
# ============================================================

def icon_at(
    icons,
    x,
    y,
):
    """
    指定座標のアイコンを返す
    """

    for icon in icons:

        if (
            icon["x"] <= x <= icon["x"] + 17
            and
            icon["y"] <= y <= icon["y"] + 1
        ):
            return icon

    return None


# ============================================================
# フォルダ判定
# ============================================================

def is_folder(icon):
    """
    フォルダアイコンか判定
    """

    return (
        icon is not None
        and
        icon["type"] == "folder"
    )


# ============================================================
# ファイル判定
# ============================================================

def is_file(icon):
    """
    ファイルアイコンか判定
    """

    return (
        icon is not None
        and
        icon["type"] == "file"
    )


# ============================================================
# アイコン名取得
# ============================================================

def icon_name(icon):

    if icon is None:
        return ""

    return icon.get("name", "")


# ============================================================
# アイコンパス取得
# ============================================================

def icon_path(icon):

    if icon is None:
        return ""

    return icon.get("path", "")


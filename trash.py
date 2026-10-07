# ============================================================
# trash.py
# Macintosh Finder風 Trash 管理
#
# Arch Linux / Raspberry Pi OS Lite 対応
#
# Linux標準Trash仕様:
#
# ~/.local/share/Trash/
# ├── files/
# └── info/
#
# send2trash が利用可能なら send2trash を使用。
# 利用できない場合は、このファイル自身が
# Linux標準Trash形式でゴミ箱処理を行う。
# ============================================================

import os
import shutil
import urllib.parse
from datetime import datetime

from constants import (
    TRASH_PATH,
    TRASH_SYMBOL_EMPTY,
    TRASH_SYMBOL_FULL,
)


# ============================================================
# send2trash
# ============================================================

try:

    from send2trash import send2trash

    SEND2TRASH_AVAILABLE = True

except ImportError:

    SEND2TRASH_AVAILABLE = False


# ============================================================
# Trashディレクトリ
# ============================================================

TRASH_INFO_PATH = os.path.expanduser(
    "~/.local/share/Trash/info"
)


# ============================================================
# Trash存在確認
# ============================================================

def ensure_trash():
    """
    Linux標準Trashディレクトリを作成する。
    """

    try:

        os.makedirs(
            TRASH_PATH,
            exist_ok=True,
        )

        os.makedirs(
            TRASH_INFO_PATH,
            exist_ok=True,
        )

        return True

    except OSError:

        return False


# ============================================================
# 重複しないファイル名を作る
# ============================================================

def unique_trash_name(name):
    """
    Trash/files 内で重複しない名前を生成する。
    """

    destination = os.path.join(
        TRASH_PATH,
        name,
    )

    if not os.path.exists(destination):

        return name

    base, extension = os.path.splitext(
        name
    )

    number = 1

    while True:

        new_name = (
            f"{base} ({number}){extension}"
        )

        destination = os.path.join(
            TRASH_PATH,
            new_name,
        )

        if not os.path.exists(destination):

            return new_name

        number += 1


# ============================================================
# .trashinfo ファイル名
# ============================================================

def info_filename(name):

    return name + ".trashinfo"


# ============================================================
# .trashinfo を作成
# ============================================================

def create_trash_info(
    trash_name,
    original_path,
):
    """
    Linux標準形式の .trashinfo を作成する。
    """

    info_path = os.path.join(
        TRASH_INFO_PATH,
        info_filename(trash_name),
    )

    try:

        encoded_path = urllib.parse.quote(
            os.path.abspath(original_path),
            safe="/",
        )

        deletion_date = datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        content = (
            "[Trash Info]\n"
            f"Path={encoded_path}\n"
            f"DeletionDate={deletion_date}\n"
        )

        with open(
            info_path,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(content)

        return True

    except OSError:

        return False


# ============================================================
# .trashinfo を読み込む
# ============================================================

def read_trash_info(name):
    """
    Trashアイテムの元のパスを取得する。
    """

    info_path = os.path.join(
        TRASH_INFO_PATH,
        info_filename(name),
    )

    if not os.path.exists(info_path):

        return None

    try:

        with open(
            info_path,
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                line = line.strip()

                if line.startswith("Path="):

                    encoded_path = line[5:]

                    return urllib.parse.unquote(
                        encoded_path
                    )

    except OSError:

        pass

    return None


# ============================================================
# ファイルをゴミ箱へ送る
# ============================================================

def move_to_trash(path):
    """
    ファイルまたはディレクトリをTrashへ移動する。

    send2trash が利用可能ならそれを使用。
    それ以外ではLinux標準Trash形式を自前で実装。
    """

    if not os.path.exists(path):

        return False

    if not ensure_trash():

        return False

    path = os.path.abspath(path)

    try:

        # ----------------------------------------------------
        # send2trash
        # ----------------------------------------------------

        if SEND2TRASH_AVAILABLE:

            send2trash(path)

            return True

        # ----------------------------------------------------
        # Linux標準Trash形式を自前で実装
        # ----------------------------------------------------

        original_path = path

        name = os.path.basename(path)

        trash_name = unique_trash_name(
            name
        )

        destination = os.path.join(
            TRASH_PATH,
            trash_name,
        )

        # ----------------------------------------------------
        # まず元ファイルを移動
        # ----------------------------------------------------

        shutil.move(
            path,
            destination,
        )

        # ----------------------------------------------------
        # .trashinfo 作成
        # ----------------------------------------------------

        if not create_trash_info(
            trash_name,
            original_path,
        ):

            # ------------------------------------------------
            # .trashinfo が作れなかった場合、
            # 元の場所へ戻す
            # ------------------------------------------------

            try:

                shutil.move(
                    destination,
                    original_path,
                )

            except Exception:

                pass

            return False

        return True

    except Exception:

        return False


# ============================================================
# Trash内部一覧
# ============================================================

def list_trash():
    """
    Trash/files のアイテム一覧を取得する。
    """

    if not ensure_trash():

        return []

    try:

        return sorted(
            os.listdir(TRASH_PATH)
        )

    except OSError:

        return []


# ============================================================
# ゴミ箱アイテム数
# ============================================================

def trash_count():

    return len(
        list_trash()
    )


# ============================================================
# 空判定
# ============================================================

def trash_empty():

    return trash_count() == 0


# ============================================================
# Finder用シンボル
# ============================================================

def trash_symbol():

    if trash_empty():

        return TRASH_SYMBOL_EMPTY

    return TRASH_SYMBOL_FULL


# ============================================================
# Finder用アイコン
# ============================================================

def make_trash_icon(
    x,
    y,
):
    """
    デスクトップ用Trashアイコンを生成する。
    """

    return {
        "name": "Trash",
        "path": TRASH_PATH,
        "symbol": trash_symbol(),
        "type": "trash",
        "x": x,
        "y": y,
    }


# ============================================================
# Trashフォルダパス取得
# ============================================================

def trash_folder():

    ensure_trash()

    return TRASH_PATH


# ============================================================
# ファイル名存在確認
# ============================================================

def trash_contains(name):

    path = os.path.join(
        TRASH_PATH,
        name,
    )

    return os.path.exists(path)


# ============================================================
# ゴミ箱から復元
# ============================================================

def restore_from_trash(name):
    """
    Trashから元の場所へファイルを復元する。
    """

    if not ensure_trash():

        return False

    trash_file = os.path.join(
        TRASH_PATH,
        name,
    )

    if not os.path.exists(trash_file):

        return False

    # --------------------------------------------------------
    # 元の場所を取得
    # --------------------------------------------------------

    original_path = read_trash_info(
        name
    )

    if not original_path:

        return False

    try:

        # ----------------------------------------------------
        # 元のディレクトリ
        # ----------------------------------------------------

        original_directory = os.path.dirname(
            original_path
        )

        if original_directory:

            os.makedirs(
                original_directory,
                exist_ok=True,
            )

        # ----------------------------------------------------
        # 元の場所に同名ファイルがある場合
        # ----------------------------------------------------

        destination = original_path

        if os.path.exists(destination):

            base, extension = os.path.splitext(
                original_path
            )

            number = 1

            while True:

                destination = (
                    f"{base} ({number}){extension}"
                )

                if not os.path.exists(
                    destination
                ):

                    break

                number += 1

        # ----------------------------------------------------
        # 復元
        # ----------------------------------------------------

        shutil.move(
            trash_file,
            destination,
        )

        # ----------------------------------------------------
        # .trashinfo 削除
        # ----------------------------------------------------

        info_path = os.path.join(
            TRASH_INFO_PATH,
            info_filename(name),
        )

        try:

            os.remove(
                info_path
            )

        except OSError:

            pass

        return True

    except Exception:

        return False


# ============================================================
# ゴミ箱を空にする
# ============================================================

def empty_trash():
    """
    Trash/files と Trash/info を空にする。
    """

    if not ensure_trash():

        return False

    success = True

    # --------------------------------------------------------
    # Trash/files
    # --------------------------------------------------------

    try:

        for name in os.listdir(
            TRASH_PATH
        ):

            path = os.path.join(
                TRASH_PATH,
                name,
            )

            try:

                if os.path.isdir(path):

                    shutil.rmtree(path)

                else:

                    os.remove(path)

            except OSError:

                success = False

    except OSError:

        success = False

    # --------------------------------------------------------
    # Trash/info
    # --------------------------------------------------------

    try:

        for name in os.listdir(
            TRASH_INFO_PATH
        ):

            path = os.path.join(
                TRASH_INFO_PATH,
                name,
            )

            try:

                if os.path.isfile(path):

                    os.remove(path)

            except OSError:

                success = False

    except OSError:

        success = False

    return success


# ============================================================
# ゴミ箱情報
# ============================================================

def trash_status():
    """
    Trashの状態を辞書で返す。
    """

    count = trash_count()

    return {
        "count": count,
        "empty": count == 0,
        "symbol": trash_symbol(),
    }


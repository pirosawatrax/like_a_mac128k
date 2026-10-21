# ============================================================
# trash.py
# Macintosh Finder風 Trash 管理 (XDG Trash 準拠)
#
# ~/.local/share/Trash/{files,info}
#
# 状態確認はキャッシュする (毎フレーム listdir しない: Pi Zero 対策)
# ============================================================

import os
import shutil
import time
import urllib.parse
from datetime import datetime

from constants import (
    HOME,
    TRASH_PATH,
    TRASH_INFO_PATH,
    TRASH_SYMBOL_EMPTY,
    TRASH_SYMBOL_FULL,
)

try:
    from send2trash import send2trash as _send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    SEND2TRASH_AVAILABLE = False


CACHE_SECONDS = 2.0

_ensured = False
_cache = {"count": 0, "time": -1e9}


def invalidate_cache():
    _cache["time"] = -1e9


# ============================================================
# Trash ディレクトリ
# ============================================================

def ensure_trash():

    global _ensured

    if _ensured and os.path.isdir(TRASH_PATH):
        return True

    try:
        os.makedirs(TRASH_PATH, exist_ok=True)
        os.makedirs(TRASH_INFO_PATH, exist_ok=True)
    except OSError:
        return False

    _ensured = True
    return True


def list_trash():

    if not ensure_trash():
        return []

    try:
        return sorted(os.listdir(TRASH_PATH))
    except OSError:
        return []


def trash_count():
    """件数 (最大 CACHE_SECONDS 秒キャッシュ)"""

    now = time.monotonic()

    if now - _cache["time"] > CACHE_SECONDS:
        _cache["count"] = len(list_trash())
        _cache["time"] = now

    return _cache["count"]


def trash_empty():
    return trash_count() == 0


def trash_symbol():
    return TRASH_SYMBOL_EMPTY if trash_empty() else TRASH_SYMBOL_FULL


# ============================================================
# .trashinfo
# ============================================================

def info_path_for(name):
    return os.path.join(TRASH_INFO_PATH, name + ".trashinfo")


def create_trash_info(trash_name, original_path):

    try:
        encoded = urllib.parse.quote(
            os.path.abspath(original_path),
            safe="/",
        )

        date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        with open(info_path_for(trash_name), "w", encoding="utf-8") as f:
            f.write("[Trash Info]\nPath={}\nDeletionDate={}\n".format(
                encoded, date))

        return True

    except OSError:
        return False


def read_trash_info(name):

    try:
        with open(info_path_for(name), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Path="):
                    return urllib.parse.unquote(line[5:])
    except OSError:
        pass

    return None


def forget_trash_item(name):
    """Trash から外に持ち出したアイテムの .trashinfo を消す"""

    try:
        os.remove(info_path_for(name))
    except OSError:
        pass

    invalidate_cache()


def unique_trash_name(name):

    def taken(candidate):
        return (
            os.path.lexists(os.path.join(TRASH_PATH, candidate))
            or os.path.exists(info_path_for(candidate))
        )

    if not taken(name):
        return name

    base, extension = os.path.splitext(name)
    number = 1

    while True:

        candidate = "{} ({}){}".format(base, number, extension)

        if not taken(candidate):
            return candidate

        number += 1


# ============================================================
# ゴミ箱へ送る
# ============================================================

def move_to_trash(path):
    """
    ゴミ箱へ移動する。
    成功したら Trash/files 内での名前 (Undo 用) を返す。失敗は None。
    """

    path = os.path.abspath(path)

    if not os.path.lexists(path):
        return None

    # 危険なものは捨てさせない
    if path in (HOME, "/", TRASH_PATH):
        return None

    if TRASH_PATH.startswith(path + os.sep):
        return None

    if not ensure_trash():
        return None

    try:

        if SEND2TRASH_AVAILABLE:

            before = set(list_trash())
            _send2trash(path)
            added = set(list_trash()) - before
            invalidate_cache()

            if len(added) == 1:
                return added.pop()

            return os.path.basename(path)

        name = unique_trash_name(os.path.basename(path))
        destination = os.path.join(TRASH_PATH, name)

        # 仕様どおり .trashinfo を先に作る
        if not create_trash_info(name, path):
            return None

        try:
            shutil.move(path, destination)
        except (OSError, shutil.Error):
            forget_trash_item(name)
            return None

        invalidate_cache()
        return name

    except Exception:
        invalidate_cache()
        return None


# ============================================================
# 復元
# ============================================================

def restore_from_trash(name):
    """元の場所へ戻す。成功したら戻した先のパスを返す。"""

    if not ensure_trash():
        return None

    source = os.path.join(TRASH_PATH, name)

    if not os.path.lexists(source):
        return None

    original = read_trash_info(name)

    if not original:
        return None

    try:

        directory = os.path.dirname(original)

        if directory:
            os.makedirs(directory, exist_ok=True)

        destination = original

        if os.path.lexists(destination):

            base, extension = os.path.splitext(original)
            number = 1

            while os.path.lexists(destination):
                destination = "{} ({}){}".format(base, number, extension)
                number += 1

        shutil.move(source, destination)

    except (OSError, shutil.Error):
        return None

    forget_trash_item(name)
    return destination


# ============================================================
# ゴミ箱を空にする
# ============================================================

def empty_trash():

    if not ensure_trash():
        return False

    success = True

    for directory in (TRASH_PATH, TRASH_INFO_PATH):

        try:
            names = os.listdir(directory)
        except OSError:
            success = False
            continue

        for name in names:

            path = os.path.join(directory, name)

            try:
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except OSError:
                success = False

    invalidate_cache()
    return success

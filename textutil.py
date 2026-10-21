# ============================================================
# textutil.py
# 全角(日本語)対応の文字列ユーティリティ と 安全な描画関数
# ============================================================

import curses
import unicodedata


def char_width(ch):
    """1文字の表示幅 (全角=2, 結合文字=0, それ以外=1)"""

    if unicodedata.combining(ch):
        return 0

    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2

    return 1


def text_width(text):
    return sum(char_width(ch) for ch in text)


def fit(text, width):
    """表示幅が width に収まるように切り詰める"""

    if width <= 0:
        return ""

    out = []
    used = 0

    for ch in text:

        w = char_width(ch)

        if used + w > width:
            break

        out.append(ch)
        used += w

    return "".join(out)


def pad(text, width):
    text = fit(text, width)
    return text + " " * (width - text_width(text))


def put(stdscr, y, x, text, width=None, attr=0):
    """
    画面外にはみ出さないように描画する。
    curses.error は握りつぶす (右下隅への書き込み対策)。
    """

    height, screen_w = stdscr.getmaxyx()

    if y < 0 or y >= height or x >= screen_w:
        return

    if x < 0:

        chars = list(text)

        while chars and x < 0:
            x += char_width(chars.pop(0))

        text = "".join(chars)

        if x < 0:
            return

    limit = screen_w - x

    if width is not None:
        limit = min(limit, width)

    text = fit(text, limit)

    if not text:
        return

    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass

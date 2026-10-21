# ============================================================
# keyboard_mouse.py
# キーボード → 仮想マウスイベント
#
# curses.ungetmouse は使わない。
# (ncurses 内部キューの順序・端末のマウス対応有無に左右されるため)
# 代わりに自前の FIFO キューへ積み、main ループが直接処理する。
#
#   W/A/S/D : ポインタ移動 (ボタン押下中なら移動イベントも出す)
#   Space   : クリック (press → release)
#   G       : 左ボタン 押す / 離す
#   ↑ / ↓   : ホイール
# ============================================================

import curses
from collections import deque

WHEEL_UP = getattr(curses, "BUTTON4_PRESSED", 0)
WHEEL_DOWN = getattr(curses, "BUTTON5_PRESSED", 0)
MOTION = getattr(curses, "REPORT_MOUSE_POSITION", 0)


class KeyboardMouse:

    def __init__(self, x=1, y=1):

        self.x = x
        self.y = y
        self.left_button_down = False

        # (id, x, y, z, bstate) — curses.getmouse() と同じ形式
        self.queue = deque()

    # --------------------------------------------------------

    def sync(self, x, y):
        """実マウス等で動いた位置に合わせる"""
        self.x = x
        self.y = y

    def move(self, key, width, height):

        dx = 0
        dy = 0

        if key in (ord("w"), ord("W")):
            dy = -1
        elif key in (ord("s"), ord("S")):
            dy = 1
        elif key in (ord("a"), ord("A")):
            dx = -1
        elif key in (ord("d"), ord("D")):
            dx = 1
        else:
            return False

        self.x = max(1, min(width - 2, self.x + dx))
        self.y = max(1, min(height - 2, self.y + dy))

        # ドラッグ中はアイコン等が追従するよう移動イベントを出す
        if self.left_button_down:
            self._event(MOTION)

        return True

    def click(self):
        self._event(curses.BUTTON1_PRESSED)
        self._event(curses.BUTTON1_RELEASED)

    def press_left(self):

        if self.left_button_down:
            return

        self.left_button_down = True
        self._event(curses.BUTTON1_PRESSED)

    def release_left(self):

        if not self.left_button_down:
            return

        self.left_button_down = False
        self._event(curses.BUTTON1_RELEASED)

    def toggle_drag(self):

        if self.left_button_down:
            self.release_left()
        else:
            self.press_left()

    def scroll_up(self):
        self._event(WHEEL_UP)

    def scroll_down(self):
        self._event(WHEEL_DOWN)

    def heal(self, dragging):
        """
        何もドラッグしていないのに「押した状態」で残らないようにする
        (空きスペースで G を押した、Esc でドラッグを取り消した、など)
        """

        if self.left_button_down and not dragging:
            self.left_button_down = False

    def _event(self, button):
        self.queue.append((0, self.x, self.y, 0, button))

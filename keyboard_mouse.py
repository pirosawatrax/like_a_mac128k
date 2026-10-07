import curses


class KeyboardMouse:
    """
    キーボード入力をcursesのマウス操作へ変換する。

    W/S/A/D  : マウスカーソル移動
    ↑ / ↓    : ホイール
    G        : 左ボタン押下 / 離す
    Space    : 左クリック
    """

    def __init__(self, x=1, y=1):

        self.x = x
        self.y = y

        self.left_button_down = False

    # --------------------------------------------------------
    # マウスカーソル移動
    # --------------------------------------------------------

    def move(self, key, width, height):

        if key in (ord("w"), ord("W")):
            self.y -= 1

        elif key in (ord("s"), ord("S")):
            self.y += 1

        elif key in (ord("a"), ord("A")):
            self.x -= 1

        elif key in (ord("d"), ord("D")):
            self.x += 1

        else:
            return False

        # 画面外へ出ないようにする

        self.x = max(
            1,
            min(width - 2, self.x)
        )

        self.y = max(
            1,
            min(height - 2, self.y)
        )

        return True

    # --------------------------------------------------------
    # 左クリック
    # --------------------------------------------------------

    def click(self):

        self._mouse_event(
            curses.BUTTON1_PRESSED
        )

        self._mouse_event(
            curses.BUTTON1_RELEASED
        )

    # --------------------------------------------------------
    # 左ボタン押下
    # --------------------------------------------------------

    def press_left(self):

        if self.left_button_down:
            return

        self.left_button_down = True

        self._mouse_event(
            curses.BUTTON1_PRESSED
        )

    # --------------------------------------------------------
    # 左ボタン離す
    # --------------------------------------------------------

    def release_left(self):

        if not self.left_button_down:
            return

        self.left_button_down = False

        self._mouse_event(
            curses.BUTTON1_RELEASED
        )

    # --------------------------------------------------------
    # Gキー
    # --------------------------------------------------------

    def toggle_drag(self):

        if self.left_button_down:
            self.release_left()
        else:
            self.press_left()

    # --------------------------------------------------------
    # ホイール上
    # --------------------------------------------------------

    def scroll_up(self):

        self._mouse_event(
            curses.BUTTON4_PRESSED
        )

    # --------------------------------------------------------
    # ホイール下
    # --------------------------------------------------------

    def scroll_down(self):

        self._mouse_event(
            curses.BUTTON5_PRESSED
        )

    # --------------------------------------------------------
    # 仮想マウスイベントを発生
    # --------------------------------------------------------

    def _mouse_event(self, button):

        try:

            curses.ungetmouse(
                0,
                self.x,
                self.y,
                0,
                button,
            )

        except curses.error:

            pass

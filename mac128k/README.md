# like_a_mac128K TUI

A Macintosh 128K-inspired file manager for Linux terminals, written in Python and `curses`.
Runs on ordinary Linux (tested on Arch Linux) and on a Raspberry Pi Zero.

## Requirements

* Linux, Python 3.7+ (Raspberry Pi OS Buster or newer), `curses`
* Optional: `tmux` (external programs open in a new tmux window; without tmux
  the screen is suspended and the program runs in the foreground)
* Optional: `nano` (or set `$EDITOR`), `chafa`, `ffmpeg`, `mpv`, `send2trash`

```bash
# Arch
sudo pacman -S python tmux nano chafa ffmpeg mpv
# Raspberry Pi OS / Debian
sudo apt install python3 tmux nano chafa ffmpeg mpv
```

## Running

```bash
python3 main.py          # directly
./mac128k_start.sh       # inside a tmux session (Esc delay is reduced)
```

## Keyboard mouse

| Key | Function |
| --- | --- |
| `W` `A` `S` `D` | Move pointer (the dragged item follows while the button is held) |
| `Space` | Left click (press + release) |
| `G` | Press / release left button (drag & drop) |
| `Up` / `Down` | Mouse wheel |
| `Enter` | Open selected item |
| `Esc` | Cancel drag / close menu / close top window |
| `Q` | Quit (asks for confirmation) |

Dialogs: `Y` / `Enter` = Yes, `N` / `Esc` = No.
While a dialog or the Rename box is open, `W A S D G Space` are typed as text.

The keyboard mouse no longer uses `curses.ungetmouse()`. Events go through an
internal queue, so behaviour does not depend on the ncurses version or on
whether the terminal supports the mouse.

## What changed from the previous version

* Keyboard mouse: own event queue, drag follows keyboard movement, pointer
  position synced with a real mouse, stuck button state self-heals
* Rename: no key conflicts, Japanese input (`get_wch`), cursor movement
* Wide (CJK) characters are measured by display width
* Trash status is cached (no `listdir` per frame); drop-to-Trash works from windows too
* Clicking a folder no longer tries to move it into itself
* Executables / scripts ask for confirmation before running
* Desktop scrolls (wheel) instead of stacking overflowing icons; dotfiles hidden
  by default (View > Show Hidden)
* Icon positions are preserved across file operations
* Multi-level Undo (move / trash / rename / copy)
* Terminal resize is handled; `Esc` responds quickly (`ESCDELAY`)
* Events are batched: many queued mouse-move events cause only one redraw

## Files

```text
main.py            entry point, main loop, key reading
events.py          mouse / keyboard handling, file operations, menu actions
desktop.py         desktop drawing and layout calculations
windows.py         Finder-style windows
menu.py            menu bar
trash.py           XDG Trash (send2trash optional)
launcher.py        opening files (tmux window or foreground)
filesystem.py      directory reading, icon layout
keyboard_mouse.py  keyboard -> virtual mouse events
textutil.py        display-width helpers, safe drawing
constants.py       settings and symbols
mac128k_start.sh / chafa_video.sh
```

## Reporting problems

Please include `uname -a`, `python3 --version`, `echo "$TERM"`, and
`python3 -c "import curses; print(curses.ncurses_version)"`.

## License

Free to use, modify, and redistribute.

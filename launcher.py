# ============================================================
# launcher.py
# 外部プログラムの起動
#
#   tmux の中     : tmux new-window で別ウィンドウに起動
#   tmux の外     : curses を一時停止して前面で実行 (tmux 不要)
# ============================================================

import curses
import os
import shlex
import shutil
import subprocess
import sys

from constants import PROJECT_DIR


IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
VIDEO_EXT = (".mp4", ".mkv", ".webm", ".avi", ".mov")
AUDIO_EXT = (".wav", ".mp3", ".flac", ".ogg", ".m4a")
TEXT_EXT = (".txt", ".md", ".ini", ".conf", ".cfg", ".log", ".csv",
            ".json", ".xml", ".html", ".css")
EDIT_EXT = TEXT_EXT + (".py", ".sh")

# 実行系は誤ダブルクリックが怖いので確認ダイアログを出す
CONFIRM_KINDS = ("python", "shell", "exec")


def shell_join(argv):
    # shlex.join は Python 3.8+ なので自前 (Pi OS Buster は 3.7)
    return " ".join(shlex.quote(a) for a in argv)


def classify(path):

    lower = path.lower()

    if lower.endswith(IMAGE_EXT):
        return "image"
    if lower.endswith(VIDEO_EXT):
        return "video"
    if lower.endswith(AUDIO_EXT):
        return "audio"
    if lower.endswith(".py"):
        return "python"
    if lower.endswith(".sh"):
        return "shell"
    if lower.endswith(TEXT_EXT):
        return "text"
    if os.access(path, os.X_OK):
        return "exec"

    return None


def with_banner(command, title):

    script = (
        command + "; status=$?; echo; "
        "echo '================================'; "
        'echo "' + title + ' finished (exit code: $status)"; '
        "echo '================================'; "
        "echo; echo 'Press Enter to close'; read -r"
    )

    return ["bash", "-c", script]


def editor_argv():
    return shlex.split(os.environ.get("EDITOR") or "nano")


def build_command(path, kind):
    """(argv, 必要なコマンド一覧)"""

    quoted = shlex.quote(path)

    if kind == "image":
        script = "chafa {}; echo; echo 'Press Enter to close'; read -r"
        return ["bash", "-c", script.format(quoted)], ["chafa"]

    if kind == "video":
        script = os.path.join(PROJECT_DIR, "chafa_video.sh")
        return ["bash", script, path], ["ffmpeg", "chafa"]

    if kind == "audio":
        return ["mpv", "--no-video", path], ["mpv"]

    if kind == "python":
        return with_banner(
            shell_join([sys.executable, path]), "Python"), []

    if kind == "shell":
        return with_banner("bash " + quoted, "Shell script"), []

    if kind == "exec":
        return with_banner(quoted, "Program"), []

    argv = editor_argv() + [path]
    return argv, [argv[0]]


# ============================================================
# 実行
# ============================================================

def run_external(stdscr, argv, cwd=None):
    """(成功か, エラーメッセージ)"""

    if os.environ.get("TMUX") and shutil.which("tmux"):

        cmd = ["tmux", "new-window"]

        if cwd:
            cmd += ["-c", cwd]

        # 文字列 1 つで渡す (古い tmux でも動く)
        cmd.append(shell_join(argv))

        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, str(error)

        if result.returncode != 0:
            text = result.stderr.decode("utf-8", "replace").strip()
            return False, text.splitlines()[0] if text else "tmux failed"

        return True, ""

    # tmux 外: curses を止めて前面で実行する
    error = ""

    curses.def_prog_mode()
    curses.endwin()

    try:
        subprocess.call(argv, cwd=cwd)
    except OSError as e:
        error = str(e)
    finally:
        curses.reset_prog_mode()
        stdscr.clearok(True)
        stdscr.refresh()
        curses.flushinp()

    return (error == ""), error


def launch_file(stdscr, state, path):

    name = os.path.basename(path)

    if not os.path.isfile(path):
        state["message"] = "Not a file: " + name
        return False

    kind = classify(path)

    if kind is None:
        state["message"] = "Cannot open: " + name
        return False

    argv, needs = build_command(path, kind)

    missing = [t for t in needs if shutil.which(t) is None]

    if missing:
        state["message"] = "Not installed: " + ", ".join(missing)
        return False

    ok, error = run_external(stdscr, argv, cwd=os.path.dirname(path))

    state["message"] = (
        ("Launched: " + name) if ok
        else ("Could not launch: " + name + " (" + error + ")")
    )

    return ok


def request_launch(stdscr, state, path):
    """実行系は確認ダイアログを経由、それ以外は即起動"""

    kind = classify(path)

    if kind in CONFIRM_KINDS:

        state["dialog"] = {
            "type": "confirm",
            "message": "Run {}?".format(os.path.basename(path)),
            "action": "run",
            "path": path,
        }

        return

    launch_file(stdscr, state, path)


def edit_file(stdscr, state, path):

    name = os.path.basename(path)

    if not os.path.isfile(path):
        state["message"] = "Not a file: " + name
        return False

    if not path.lower().endswith(EDIT_EXT):
        state["message"] = "Cannot edit: " + name
        return False

    argv = editor_argv() + [path]

    if shutil.which(argv[0]) is None:
        state["message"] = "Not installed: " + argv[0]
        return False

    ok, error = run_external(stdscr, argv, cwd=os.path.dirname(path))

    state["message"] = (
        ("Editing: " + name) if ok
        else ("Could not edit: " + name + " (" + error + ")")
    )

    return ok

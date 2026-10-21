#!/usr/bin/env bash
# tmux 経由で起動する (tmux は必須ではありません: python3 main.py でも動きます)

SESSION="mac128k"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed. Running without tmux."
    cd "$SCRIPT_DIR" && exec python3 main.py
fi

if [ -n "$TMUX" ]; then
    CURRENT_SESSION="$(tmux display-message -p '#S')"

    if [ "$CURRENT_SESSION" = "$SESSION" ]; then
        echo "Already inside $SESSION tmux session."
        exit 0
    fi

    echo "Already inside another tmux session: $CURRENT_SESSION"
    echo "Run directly instead:  cd \"$SCRIPT_DIR\" && python3 main.py"
    exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
    exec tmux attach-session -t "$SESSION"
fi

# python を直接セッションのコマンドにする (終了するとセッションも閉じる)
tmux new-session -d -s "$SESSION" -c "$SCRIPT_DIR" "python3 main.py"

# Esc の遅延を減らす (既定 500ms)
tmux set-option -s escape-time 10

exec tmux attach-session -t "$SESSION"

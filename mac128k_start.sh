#!/bin/bash

SESSION="mac128k"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ------------------------------------------------------------
# tmux がインストールされているか確認
# ------------------------------------------------------------

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed."
    echo
    echo "Install it with:"
    echo "  sudo pacman -S tmux"
    echo
    exit 1
fi

# ------------------------------------------------------------
# すでにtmuxの中にいる場合
# ------------------------------------------------------------

if [ -n "$TMUX" ]; then

    # すでにmac128kセッションなら、そのまま使用
    CURRENT_SESSION="$(tmux display-message -p '#S')"

    if [ "$CURRENT_SESSION" = "$SESSION" ]; then
        echo "Already inside $SESSION tmux session."
        exit 0
    fi

    # 別のtmuxセッションから実行した場合
    echo "Already inside another tmux session:"
    echo "  $CURRENT_SESSION"
    echo
    echo "Exit tmux first, then run:"
    echo
    echo "  ./mac128k_start.sh"
    echo

    exit 1
fi

# ------------------------------------------------------------
# すでにmac128kセッションが存在する場合
# ------------------------------------------------------------

if tmux has-session -t "$SESSION" 2>/dev/null; then

    tmux attach-session -t "$SESSION"

    exit 0
fi

# ------------------------------------------------------------
# 新しいtmuxセッションを作成
# ------------------------------------------------------------

tmux new-session \
    -d \
    -s "$SESSION" \
    -c "$SCRIPT_DIR"

# ------------------------------------------------------------
# Macintosh TUIを起動
# ------------------------------------------------------------

tmux send-keys \
    -t "$SESSION:0" \
    "python3 main.py" \
    C-m

# ------------------------------------------------------------
# Macintosh TUIへ接続
# ------------------------------------------------------------

tmux attach-session \
    -t "$SESSION"


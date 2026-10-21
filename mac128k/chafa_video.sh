#!/usr/bin/env bash
# ffmpeg で 1 フレームずつ JPEG を作り、chafa で表示する。
# q で停止。ffmpeg が先走ってディスク/RAM を使い切らないよう一時停止で制御する。

VIDEO="$1"

if [ ! -f "$VIDEO" ]; then
    echo "Video not found:"
    echo "$VIDEO"
    echo
    read -r -p "Press Enter to close..."
    exit 1
fi

TEMP_DIR=$(mktemp -d)
FFMPEG_PID=""

cleanup() {
    if [ -n "$FFMPEG_PID" ]; then
        kill -CONT "$FFMPEG_PID" 2>/dev/null
        kill "$FFMPEG_PID" 2>/dev/null
    fi
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

ffmpeg -loglevel error -i "$VIDEO" \
    -vf "fps=5,scale='min(480,iw)':-2" \
    "$TEMP_DIR/frame_%06d.jpg" &
FFMPEG_PID=$!

FRAME_NUMBER=1
STOPPED=0

while true; do

    FRAME=$(printf "%s/frame_%06d.jpg" "$TEMP_DIR" "$FRAME_NUMBER")

    # 先読みしすぎたら ffmpeg を止め、減ったら再開する
    AHEAD=$(find "$TEMP_DIR" -name 'frame_*.jpg' | wc -l)

    if [ "$AHEAD" -gt 60 ] && [ "$STOPPED" -eq 0 ]; then
        kill -STOP "$FFMPEG_PID" 2>/dev/null; STOPPED=1
    elif [ "$AHEAD" -lt 20 ] && [ "$STOPPED" -eq 1 ]; then
        kill -CONT "$FFMPEG_PID" 2>/dev/null; STOPPED=0
    fi

    # フレームが生成されるまで待つ
    while [ ! -f "$FRAME" ]; do
        if ! kill -0 "$FFMPEG_PID" 2>/dev/null; then
            [ -f "$FRAME" ] || break 2
        fi
        sleep 0.02
    done

    clear
    chafa "$FRAME"
    CHAFA_STATUS=$?

    if [ "$CHAFA_STATUS" -ne 0 ]; then
        echo
        echo "chafa error. Exit code: $CHAFA_STATUS"
        break
    fi

    rm -f "$FRAME"
    FRAME_NUMBER=$((FRAME_NUMBER + 1))

    # 5fps。待ち時間中に q が押されたら終了
    if read -r -s -n 1 -t 0.2 KEY && [ "$KEY" = "q" ]; then
        echo "Stopped."
        break
    fi

done

kill -CONT "$FFMPEG_PID" 2>/dev/null
wait "$FFMPEG_PID" 2>/dev/null
FFMPEG_STATUS=$?

echo
echo "================================"
if [ "$FFMPEG_STATUS" -eq 0 ] || [ "$FFMPEG_STATUS" -eq 143 ]; then
    echo "End of video."
else
    echo "Video playback error. ffmpeg exit code: $FFMPEG_STATUS"
fi
echo "================================"
echo
echo "Press Enter to close."
read -r

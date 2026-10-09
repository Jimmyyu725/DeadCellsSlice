#!/bin/zsh
# Rebuild content + scene + macOS player, then run the autoplay demo and
# capture frames. Usage: Tools/build_and_capture.sh <run-name> [burstStart burstEnd] [--skip-build]
set -e
cd "$(dirname "$0")/.."
NAME=${1:-run}
BURST_START=${2:--1}
BURST_END=${3:--1}
UNITY=~/.unity/bin/unity
if [[ "$4" != "--skip-build" ]]; then
  $UNITY run . --no-tail -l Logs/content.log -- -executeMethod DeadCells.EditorTools.DCBatch.All >/dev/null 2>&1 || true
  grep -E "error CS|\[DC\] (build|scene|content)|errors=" Logs/content.log | tail -6
fi
OUT="$PWD/Captures/$NAME"
rm -rf "$OUT" && mkdir -p "$OUT"
"Builds/DeadCellsSlice.app/Contents/MacOS/Dead Cells Slice" -autoplay -captureDir "$OUT" -autoplaySeconds 26 \
  -captureInterval 0.5 -burst "$BURST_START" "$BURST_END" -screen-width 1920 -screen-height 1080 \
  -screen-fullscreen 0 -logFile "$OUT/player.log" &
PID=$!
for i in $(seq 1 60); do
  sleep 1
  if grep -q "^done\." "$OUT/autoplay_log.txt" 2>/dev/null; then break; fi
done
sleep 1; kill $PID 2>/dev/null || true
tail -1 "$OUT/autoplay_log.txt"
ls "$OUT" | grep -c png

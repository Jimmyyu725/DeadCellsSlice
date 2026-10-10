#!/bin/zsh
# Rebuild content + scenes + macOS player, then run the autoplay verifier and
# capture frames.
# Usage: Tools/build_and_capture.sh <run-name> [--skip-build] [--seconds N] [-- extra player args]
# Extra player args are passed through, e.g.
#   -autoplayMenu -autoplayGod -autoplaySkip 25 -autoplayBiome 2 -autoplayLang en -captureInterval 1
set -e
cd "$(dirname "$0")/.."
NAME=${1:-run}
shift || true
SKIP=0
SECONDS_RUN=60
EXTRA=()
while (( $# > 0 )); do
  case "$1" in
    --skip-build) SKIP=1 ;;
    --seconds) SECONDS_RUN=$2; shift ;;
    --) shift; EXTRA=("$@"); break ;;
  esac
  shift
done
UNITY=~/.unity/bin/unity
if (( SKIP == 0 )); then
  $UNITY run . --no-tail -l Logs/content.log -- -executeMethod DeadCells.EditorTools.DCBatch.All >/dev/null 2>&1 || true
  grep -E "error CS|\[DC\] (build|scene|content)|errors=" Logs/content.log | tail -6
fi
OUT="$PWD/Captures/$NAME"
rm -rf "$OUT" && mkdir -p "$OUT"
"${APP:-Builds/DeadCellsSlice.app}/Contents/MacOS/Dead Cells Slice" -autoplay -captureDir "$OUT" -autoplaySeconds "$SECONDS_RUN" \
  -captureInterval 2 -screen-width 1920 -screen-height 1080 -screen-fullscreen 0 -logFile "$OUT/player.log" "${EXTRA[@]}" &
PID=$!
for i in $(seq 1 $((SECONDS_RUN + 90))); do
  sleep 1
  if grep -q "^done\." "$OUT/autoplay_log.txt" 2>/dev/null; then break; fi
done
sleep 1; kill $PID 2>/dev/null || true
tail -1 "$OUT/autoplay_log.txt"
ls "$OUT" | grep -c png

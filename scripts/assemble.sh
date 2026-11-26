#!/bin/bash
# assemble.sh <project> [captions]
# Grades each run of shots that share a look with scripts/grade.py (daylight looks here, dark looks via cinematicanimation finish.py), joins them, adds the black tail, then burns
# captions and muxes the mix. Exports to out/: reel.mp4 (subtitles), reel_en.mp4 (if out/subs_en.ass), reel_labels_only.mp4,
# reel_no_voice.mp4 (labels + music and effects). `captions` = keep out/work/plates.mp4, only burn and mux again (minutes).
set -euo pipefail
P="$(cd "${1:?project}" && pwd)"; MODE="${2:-}"; export PYTHONDONTWRITEBYTECODE=1
FIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/grade.py"
[ -f "${CINE_SCRIPTS:-$HOME/.claude/skills/cinematicanimation/scripts}/finish.py" ] || { echo "cinematicanimation is not installed" >&2; exit 1; }
W="$P/out/work"; mkdir -p "$W"; FPS=$(python3 -I -c "import json; print(json.load(open('$P/audio/timeline.json'))['fps'])")
BLACK=$(python3 -I -c "import json; print(json.load(open('$P/audio/timeline.json')).get('black', 18))")
if [ "$MODE" != captions ]; then
python3 -I - "$P" > "$W/groups.txt" <<'PY'
import json, sys
g = []
for x in json.load(open(sys.argv[1]+'/audio/timeline.json'))['shots']:
    if g and g[-1][0] == x['look']: g[-1][2] = x['f1']
    else: g.append([x['look'], x['f0'], x['f1']])
for i, (l, a, b) in enumerate(g): print(i, l, a, b)
PY
: > "$W/list.txt"
while read -r i look a b; do
  D="$W/g$i"; mkdir -p "$D"; find "$D" -type l -delete
  for f in $(seq "$a" "$b"); do n=$(printf "f_%05d.jpg" "$f"); [ -f "$P/out/frames/$n" ] || { echo "missing $n" >&2; exit 1; }; ln -s "$P/out/frames/$n" "$D/$n"; done
  python3 -I -B "$FIN" "$D" --out "$W/g$i.mp4" --look "$look" --grain 3 --crf 15 --fps "$FPS" < /dev/null
  echo "file '$W/g$i.mp4'" >> "$W/list.txt"
done < "$W/groups.txt"
ffmpeg -nostdin -y -v error -f concat -safe 0 -i "$W/list.txt" \
  -vf "setpts=N/($FPS*TB),fps=$FPS,scale=in_range=pc:out_range=tv,format=yuv420p,tpad=stop=$BLACK:stop_mode=add:color=black" \
  -color_range tv -r "$FPS" -c:v libx264 -crf 14 -preset medium "$W/plates.mp4"
fi
python3 -I -B "$(dirname "${BASH_SOURCE[0]}")/captions.py" "$P"
out(){ ffmpeg -nostdin -y -v error -i "$W/plates.mp4" -i "$2" -map 0:v -map 1:a -vf "ass=$3" -c:v libx264 -preset slow -crf 17 -maxrate 14M -bufsize 28M \
  -profile:v high -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 -r "$FPS" \
  -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart "$1"; echo "wrote ${1#$P/}"; }
A="$P/audio/mix.wav"; [ -f "$A" ] || A="$P/audio/vo.wav"
out "$P/out/reel.mp4" "$A" "$P/out/subs.ass"
[ -f "$P/out/subs_en.ass" ] && out "$P/out/reel_en.mp4" "$A" "$P/out/subs_en.ass"
out "$P/out/reel_labels_only.mp4" "$A" "$P/out/labels.ass"
[ -f "$P/audio/mix_no_vo.wav" ] && out "$P/out/reel_no_voice.mp4" "$P/audio/mix_no_vo.wav" "$P/out/labels.ass"
true

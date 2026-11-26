#!/bin/bash
# render.sh <project> [ids]   Two Blender workers walk the shot list (never more: the machine is shared), then up to three
# sweeps pick up any frame a crash or a stale lock left out. Resumes: frames that exist are skipped.
# PREVIEW=1 = a quarter of the size, 16 samples (a playblast to check motion and timing in minutes).
# Run it in the background; it takes hours for a 60-80 s film (EEVEE, about 1.5-3 s a frame each worker on an M4).
set -uo pipefail
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; P="$(cd "${1:?project}" && pwd)"; IDS="${2:-}"
B="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"; O="$P/out/frames"; mkdir -p "$O" "$P/logs"
find "$O" -name '*.lock' -delete; find "$O" -name '*.part.jpg' -delete
if [ -z "$IDS" ]; then IDS=$(python3 -I -c "import json; print(','.join(s['id'] for s in json.load(open('$P/audio/timeline.json'))['shots']))"); fi
# split the list into two halves of equal frame count, longest shots first
read -r A Bl < <(python3 -I - "$P" "$IDS" <<'PY'
import json, sys
T = {s['id']: s['n'] for s in json.load(open(sys.argv[1]+'/audio/timeline.json'))['shots']}; a, b, na, nb = [], [], 0, 0
for i in sorted(sys.argv[2].split(','), key=lambda i: -T[i]):
    if na <= nb: a.append(i); na += T[i]
    else: b.append(i); nb += T[i]
print(','.join(a) or '-', ','.join(b) or '-')
PY
)
PV=""; [ "${PREVIEW:-}" = 1 ] && PV="--preview"
run(){ [ "$2" = - ] || "$B" -b --factory-startup -P "$H/blender/render.py" -- "$P" --ids "$2" $PV > "$P/logs/render_$1.log" 2>&1; }
run a "$A" & run b "$Bl" & wait
WANT=$(python3 -I -c "import json; t=json.load(open('$P/audio/timeline.json')); print(sum(s['n'] for s in t['shots'] if s['id'] in '$IDS'.split(',')))")
for k in 1 2 3; do
  HAVE=$(python3 -I -c "
import json, os; t=json.load(open('$P/audio/timeline.json'))
print(sum(os.path.exists(f'$O/f_{f:05d}.jpg') for s in t['shots'] if s['id'] in '$IDS'.split(',') for f in range(s['f0'], s['f1']+1)))")
  echo "sweep $k: $HAVE / $WANT frames"; [ "$HAVE" -ge "$WANT" ] && break
  find "$O" -name '*.lock' -delete
  "$B" -b --factory-startup -P "$H/blender/render.py" -- "$P" --ids "$IDS" $PV > "$P/logs/render_sweep$k.log" 2>&1
done
grep -h "^SHOT" "$P"/logs/render_*.log | sort | uniq
echo "RENDER DONE $(date)"

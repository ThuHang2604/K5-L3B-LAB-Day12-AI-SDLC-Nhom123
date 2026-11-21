#!/usr/bin/env bash
# Sinh bằng chứng chạy thật cho một phase: bash tools/proof.sh 1   (hoặc 2)
# Lưu vào docs/proof/phase-<n>/: kết quả test, smoke hai tiến trình (gather -> quan), commit đang chạy.
set -euo pipefail
N="${1:?dùng: tools/proof.sh <phase>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/proof/phase-$N"
mkdir -p "$OUT"
cd "$ROOT"
HL="$(python3 -c 'import json;print(json.load(open("game.contract.json"))["headless_cmd"])')"
{ echo "commit: $(git rev-parse --short HEAD 2>/dev/null || echo n/a)"; echo "date: $(date -u +%FT%TZ)"; python3 --version; } > "$OUT/env.txt"
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v > "$OUT/tests.txt" 2>&1 && echo "RESULT: PASS" >> "$OUT/tests.txt" || { echo "RESULT: FAIL" >> "$OUT/tests.txt"; }
TMP="$(mktemp -d)"
# v1.2: kho cá thể (TICKET-03): một cá linh tươi 100, cập bến ở frame 0
echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}' > "$TMP/dock.json"
echo '{"frames":[{"tick":0,"interact":true}]}' > "$TMP/dock-inputs.json"
$HL --mode gather --seed 42 --scenario "$TMP/dock.json" --inputs "$TMP/dock-inputs.json" --ticks 1 \
    --out "$OUT/integration-gather.jsonl" --inventory-out "$OUT/integration-catch.json"
$HL --mode quan --seed 42 --inventory "$OUT/integration-catch.json" --ticks 0 --out "$OUT/integration-quan.jsonl"
python3 - "$OUT" <<'PY' > "$OUT/integration-check.txt"
import json, sys
o = sys.argv[1]
inv = json.load(open(f"{o}/integration-catch.json"))
q = [json.loads(l) for l in open(f"{o}/integration-quan.jsonl")]
snap0 = next(r for r in q if r["type"] == "snapshot" and r["tick"] == 0)
print("file kho :", inv)
print("stock t0 :", snap0["stock"])
fi, st = inv["items"], snap0["stock"]
ok = ([(x["id"], x["kind"]) for x in fi] == [(x["id"], x["kind"]) for x in st] == [("I1", "ca_linh")]
      and all(abs(a["fresh"] - b["fresh"]) <= 0.01 for a, b in zip(fi, st))
      and fi[0]["fresh"] * 240 == 24000 - 2)
print("so id/kind/fresh (±0.01), fresh = 100 − 1 bước hao gather:", "ĐẠT" if ok else "CHƯA ĐẠT")
print("KẾT QUẢ  :", "ĐẠT" if ok else "CHƯA ĐẠT")
PY
# tất định: chạy lại cùng tham số, so từng byte
$HL --mode gather --seed 7 --ticks 3000 --out "$TMP/a.jsonl"
$HL --mode gather --seed 7 --ticks 3000 --out "$TMP/b.jsonl"
cmp "$TMP/a.jsonl" "$TMP/b.jsonl" && echo "deterministic gather seed 7 x3000: giống từng byte" > "$OUT/determinism.txt"
if [ "$N" -ge 2 ]; then
  start=$(date +%s.%N)
  $HL --mode day --seed 42 --days 1 --ticks 22200 --out "$OUT/day1.jsonl"
  end=$(date +%s.%N)
  echo "day --days 1 --ticks 22200: $(python3 -c "print(round($end-$start,2))") s" > "$OUT/day-timing.txt"
  tail -1 "$OUT/day1.jsonl" >> "$OUT/day-timing.txt"
  [ -f "$ROOT/tools/proof_days.py" ] && python3 "$ROOT/tools/proof_days.py" "$OUT" > "$OUT/days-upgrades.txt"
fi
if [ "$N" -ge 3 ]; then
  echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":30}],"random_fish":false,"monsters":[]}}' > "$TMP/s30.json"
  $HL --mode gather --seed 1 --scenario "$TMP/s30.json" --ticks 1 --out "$OUT/threshold-gather.jsonl"
  grep '"spoiled"' "$OUT/threshold-gather.jsonl" > "$OUT/threshold-check.txt"
  echo '{"items":{"ca_loc":1}}' > "$TMP/old.json"
  set +e; $HL --mode quan --seed 1 --inventory "$TMP/old.json" --ticks 0 --out "$TMP/x.jsonl" 2>> "$OUT/threshold-check.txt"
  echo "kho đếm v1.1 với contract v1.2 -> mã thoát $?" >> "$OUT/threshold-check.txt"; set -e
fi
if [ "$N" -ge 4 ]; then
  SC="$(python3 -c 'import json;print(json.load(open("game.contract.json"))["soak_cmd"])')"
  BC="$(python3 -c 'import json;print(json.load(open("game.contract.json"))["bench_cmd"])')"
  $SC --seed 7 --days 10 --out "$OUT/soak.json" > "$OUT/soak-stdout.txt"
  $BC --seed 42 --duration 30 --out "$OUT/bench.json" 2> "$OUT/bench-stderr.txt"
  # clone sạch: 3 lệnh theo README (clone, cd, chạy) — chạy giao diện 3 s rồi đọc /state
  { echo "\$ git clone <repo> clean && cd clean && python3 -m chonoi.live --port 8765"
    git clone -q "$ROOT" "$TMP/clean" && cd "$TMP/clean" && git log --oneline -1
    (timeout 4 python3 -m chonoi.live --port 8765 > "$TMP/live.txt" 2>&1 &)
    sleep 2.5; python3 -c "import json,urllib.request;s=json.load(urllib.request.urlopen('http://127.0.0.1:8765/state'));print('GET /state ->', s['mode'], s['phase'], 'ui_hold =', s['ui_hold'])"
    head -1 "$TMP/live.txt"
    PYTHONPATH=tests:. python3 -m unittest discover -s tests 2>&1 | tail -1
    cd "$ROOT"; } > "$OUT/clean-clone.txt" 2>&1
fi
rm -rf "$TMP"
tail -1 "$OUT/tests.txt"; cat "$OUT/integration-check.txt"

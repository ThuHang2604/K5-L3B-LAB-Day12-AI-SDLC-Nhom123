"""Bằng chứng nhiều Ngày: cấp nâng cấp mua ở Shop chỉ có hiệu lực từ Ngày kế.

    python3 tools/proof_days.py <thư-mục-ra>
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1]
c = json.load(open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8"))
dur = int(c["tuning"]["quan"]["duration_s"] * 60)
day_len = 1 + dur + 1
frames = {}
def put(t, **kw):
    frames.setdefault(t, {"tick": t}).update(kw)
for d in range(3):
    s = d * day_len
    put(s, interact=True); put(s + 1, interact=False)
    k = s + 1 + dur
    put(k, buy=["oxygen", "hp", "oxygen"][d], shop_done=True); put(k + 1, shop_done=False)
sc_path, in_path, o_path = (os.path.join(out, n) for n in ("days-scenario.json", "days-inputs.json", "days.jsonl"))
json.dump({"day": {"money": 1000, "earned": 1000}, "gather": {"random_fish": False}}, open(sc_path, "w"))
json.dump({"frames": [frames[t] for t in sorted(frames)]}, open(in_path, "w"))
cmd = [*c["headless_cmd"].split(), "--mode", "day", "--days", "3", "--seed", "1", "--scenario", sc_path,
       "--inputs", in_path, "--ticks", str(3 * day_len + 5), "--snapshot-every", "100000", "--out", o_path]
subprocess.run(cmd, check=True, cwd=ROOT)
rows = [json.loads(l) for l in open(o_path, encoding="utf-8")]
print("$", " ".join(cmd[2:]))
for r in rows:
    if r["type"] == "event" and r["name"] in ("bought", "buy_failed", "shop_end", "day_start"):
        print(f"tick {r['tick']:>6} day {r['day']} {r['name']:<10} {json.dumps(r['data'], ensure_ascii=False)}")
    if r["type"] == "snapshot" and r["phase"] == "gather" and r["phase_tick"] == 0:
        p = r["player"]
        print(f"tick {r['tick']:>6} day {r['day']} gather start: upgrades={r['upgrades']} active={r['active_upgrades']} "
              f"oxygen_max_ticks={p['oxygen_max_ticks']} hp_max={p['hp_max']} hp={p['hp']}")
end = rows[-1]
print("end:", json.dumps(end, ensure_ascii=False))
ok = end["days_completed"] == 3 and end["reason"] == "days_complete"
print("KẾT QUẢ:", "ĐẠT" if ok else "CHƯA ĐẠT")

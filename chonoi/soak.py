"""Soak headless (TICKET-04 mục 2): chạy N Ngày trong MỘT tiến trình bằng bot tất định.

    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Mỗi Ngày đi qua gather -> quan -> shop; kế hoạch D1–D5 lặp ở Ngày 6–10; tiền, earned, uy tín, cấp nâng cấp,
số Ngày và id cá thể tiếp tục xuyên suốt (một DaySim). Bot chỉ đọc trạng thái sim nên cùng seed -> cùng kết quả.
Xuất {days, days_completed, crashes, results[{day, earned, reputation, score}], duration_s}. Không ghi xếp hạng.
"""

import argparse
import json
import math
import sys
import time
import traceback

from .contract import load_contract
from .errors import BadInput
from .inputs import InputState
from .runner import Session


class Bot:
    """Bot đơn giản: sáng hái bông ở mặt nước rồi về bến; tối nấu/bưng/phục vụ; Shop mua nâng cấp rồi đóng."""

    def __init__(self, tuning):
        self.t = tuning
        self.held = {"interact": False, "shop_done": False}

    def act(self, day):
        sim = day.sub
        move, interact, buy, shop_done = (0.0, 0.0), False, None, False
        if day.phase == "gather":
            move, interact = self._gather(sim)
        elif day.phase == "quan":
            move, interact = self._quan(sim)
        else:
            buy, shop_done = self._shop(day)
        edges = set()
        for name, want in (("interact", interact), ("shop_done", shop_done)):
            if want and not self.held[name]:
                edges.add(name)
                self.held[name] = True
            else:
                self.held[name] = False
        return InputState(move, dict(self.held), edges, buy)

    @staticmethod
    def _toward(pos, target, stop=0.3):
        dx, dy = target[0] - pos[0], target[1] - pos[1]
        n = math.hypot(dx, dy)
        if n <= stop:
            return (0.0, 0.0)
        return (dx / n, dy / n)

    def _gather(self, g):
        t = self.t["gather"]
        dock = t["dock_pos"]
        back_ticks = abs(g.pos[0] - dock[0]) / t["swim_speed"] * 60 + 180
        full = len(g.hold) >= t["hold_capacity"]
        if full or g.time_left_ticks <= back_ticks:
            if math.dist(g.pos, dock) <= t["dock_radius"] * 0.8:
                return (0.0, 0.0), True
            return self._toward(g.pos, dock, 0.1), False
        ready = [n for n in g.nodes if n["regrow_ticks"] == 0]
        if not ready:
            return (0.0, -1.0), False
        n = min(ready, key=lambda n: (abs(n["pos"][0] - g.pos[0]), n["id"]))
        if math.dist(g.pos, n["pos"]) <= t["interact_radius"] * 0.8 and g.pos[1] <= t["surface_depth"]:
            return (0.0, 0.0), True
        return self._toward(g.pos, n["pos"], 0.1), False

    def _quan(self, q):
        r = self.t["quan"]["interact_radius"] * 0.8
        target = None
        if q.hand is not None:
            c = next((c for c in q.customers if c["id"] == q.hand["order_id"]), None)
            if c:
                target = next(tb["pos"] for tb in q.tables if tb["id"] == c["table_id"])
        if target is None:
            ready = [s for s in q.stoves if s["state"] == "ready"]
            if ready and q.hand is None:
                target = ready[0]["pos"]
        if target is None:
            waiting = any(c["state"] == "waiting" and c["order_status"] == "reserved" for c in q.customers)
            idle = [s for s in q.stoves if s["state"] == "idle"]
            if waiting and idle:
                target = idle[0]["pos"]
        if target is None:
            return (0.0, 0.0), False
        if math.dist(q.pos, target) <= r:
            return (0.0, 0.0), True
        return self._toward(q.pos, target, 0.1), False

    def _shop(self, day):
        if day.shop_tick == 0:
            for uid in ("oxygen", "hp"):
                lv = day.upgrades.get(uid, 0)
                levels = day.shop_t["upgrades"][uid]
                if lv < len(levels) and day.money >= levels[lv]["price"]:
                    return uid, False
            return None, False
        if day.shop_tick == 1:
            for uid in ("hp", "oxygen"):
                lv = day.upgrades.get(uid, 0)
                levels = day.shop_t["upgrades"][uid]
                if lv < len(levels) and day.money >= levels[lv]["price"]:
                    return uid, False
            return None, False
        return None, True


def soak(seed, days, tuning):
    t0 = time.perf_counter()
    sess = Session("day", tuning, {}, seed, days=days)
    bot = Bot(tuning)
    results, crashes = [], 0
    try:
        while not sess.done:
            day = sess.sim
            closed_before = day.days_completed
            rows = sess.step(bot.act(day))
            if day.days_completed > closed_before:
                results.append({"day": closed_before + 1, "earned": day.earned, "reputation": day.reputation,
                                "score": sess.score()})
            if sess.tick > days * 23_000:  # chặn vòng lặp vô hạn nếu luật hỏng
                raise RuntimeError("soak vượt số tick tối đa")
    except Exception:  # đếm crash, không làm sập tiến trình
        crashes += 1
        sys.stderr.write(traceback.format_exc())
    return {"days": days, "days_completed": sess.sim.days_completed, "crashes": crashes, "results": results,
            "duration_s": round(time.perf_counter() - t0, 3)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.soak")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--days", type=int, required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.days < 1:
        sys.stderr.write("--days phải ≥ 1\n")
        return 2
    try:
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    rep = soak(a.seed, a.days, tuning)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: rep[k] for k in ("days", "days_completed", "crashes", "duration_s")}, ensure_ascii=False))
    return 0 if rep["crashes"] == 0 and rep["days_completed"] == rep["days"] else 1


if __name__ == "__main__":
    sys.exit(main())

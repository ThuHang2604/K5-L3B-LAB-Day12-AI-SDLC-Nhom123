"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Luật nhóm đã viết (lát 3 + 4), mọi số đọc từ game.contract.json:
  - khách đến theo lịch (first_customer_tick, customer_interval_s), chọn ngẫu nhiên (luồng `customer_dish`)
    một món NẤU ĐƯỢC từ kho trừ phần đã giữ chỗ của khách khác; không món nào nấu được -> `no_dish`
  - kiên nhẫn giảm khi chờ món; hết thì `customer_left` (-uy tín, nhả giữ chỗ)
  - interact tại bếp/bàn: cook_started, dish_ready, dish_picked, served; ăn xong `paid` (+ boa, uy tín)
  - hết ca: quan_end
Quyết định chưa rõ trong PRD được ghi ở docs/clarify.md.
"""

import math

from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.tick = 0
        self.random_customers = scenario.get("random_customers", True)
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = [self._build_customer(c) for c in scenario.get("customers", [])]
        for e in self.customers:
            ids.reserve(e["id"])
        # giữ chỗ suy ra từ khách đang chờ món mà chưa nấu (trừ khi scenario khai sẵn)
        for c in self.customers:
            if "reserved" in c:
                continue
            c["reserved"] = dict(self.menu[c["dish"]]["recipe"]) if c["state"] == "assigned" and not c["cooking"] else {}
        for k, n in self._reserved_total().items():
            if n > self.stock.get(k, 0):
                from ..errors import BadInput
                raise BadInput(f"khách giữ chỗ {k} nhiều hơn kho ({n} > {self.stock.get(k, 0)})")
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": [{k: c[k] for k in ("id", "table_id", "state", "dish", "patience_ticks",
                                              "eat_ticks_left", "reserved")}
                          for c in sort_by_id(self.customers)],
        }

    def _build_customer(self, c):
        """Khách từ scenario: điền mặc định (đơn assigned, kiên nhẫn đầy)."""
        out = dict(c)
        out.setdefault("state", "assigned")
        out.setdefault("dish", None)
        out.setdefault("cooking", False)
        out.setdefault("patience_ticks", int(round(self.t["patience_s"] * TICK)))
        out.setdefault("eat_ticks_left", int(round(self.t["eat_s"] * TICK)) if out["state"] == "eating" else 0)
        if out["state"] == "eating":
            out.setdefault("tip", self._tip_for(out["dish"], out["patience_ticks"]))
            out["reserved"] = out.get("reserved", {})
        return out

    def _tip_for(self, dish, patience_left):
        total = self.t["patience_s"] * TICK
        if patience_left / total >= self.t["tip_min_patience_ratio"]:
            return int(round(self.menu[dish]["price"] * self.t["tip_rate"]))
        return 0

    def _reserved_total(self):
        total = {}
        for c in self.customers:
            for k, n in c["reserved"].items():
                total[k] = total.get(k, 0) + n
        return total

    def _available(self):
        """Kho trừ phần đã giữ chỗ của khách."""
        free = dict(self.stock)
        for c in self.customers:
            for k, n in c["reserved"].items():
                free[k] = free.get(k, 0) - n
        return free

    def _cookable(self):
        free = self._available()
        return [d for d in sorted(self.menu)
                if all(free.get(k, 0) >= n for k, n in self.menu[d]["recipe"].items())]

    def step(self, inp):
        events = []
        self.tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        # 1. bếp: đang nấu -> chín
        for s in self.stoves:
            if s["state"] == "cooking":
                s["cook_ticks_left"] -= 1
                if s["cook_ticks_left"] <= 0:
                    s["cook_ticks_left"] = 0
                    s["state"] = "ready"
                    events.append(("dish_ready", {"stove_id": s["id"], "dish": s["dish"]}))
            elif s["state"] == "ready":
                s["ready_ticks"] += 1  # burn_s = null: không cháy ở phase này
        # 2. khách theo thứ tự id: ăn / trả tiền, kiên nhẫn / bỏ đi
        for c in sort_by_id(self.customers):
            if c["state"] == "eating":
                c["eat_ticks_left"] -= 1
                if c["eat_ticks_left"] <= 0:
                    self._pay(c, events)
            else:
                c["patience_ticks"] -= 1
                if c["patience_ticks"] <= 0:
                    self._leave(c, events)
        # 3. đi lại, rồi tối đa MỘT interact
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        # 4. khách mới theo lịch
        if self.random_customers and self._arrival_tick():
            self._new_customer(events)
        # 5. hết ca
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    def _arrival_tick(self):
        first = int(self.t["first_customer_tick"])
        step = max(1, int(round(self.t["customer_interval_s"] * TICK)))
        return self.tick >= first and (self.tick - first) % step == 0

    def _set_reputation(self, delta):
        lo, hi = self.t["reputation_min"], self.t["reputation_max"]
        self.reputation = round(min(hi, max(lo, self.reputation + delta)), 6)

    def _new_customer(self, events):
        taken = {c["table_id"] for c in self.customers}
        free_tables = [tb for tb in self.tables if tb["id"] not in taken]
        if not free_tables:
            return  # không còn bàn: khách không vào quán
        dishes = self._cookable()
        if not dishes:
            events.append(("no_dish", {"stock": {k: v for k, v in sorted(self.stock.items()) if v > 0}}))
            return
        dish = self.rng.get("customer_dish").choice(dishes)
        cid = self.ids.new("C")
        c = {"id": cid, "table_id": free_tables[0]["id"], "state": "assigned", "dish": dish, "cooking": False,
             "patience_ticks": int(round(self.t["patience_s"] * TICK)), "eat_ticks_left": 0,
             "reserved": dict(self.menu[dish]["recipe"])}
        self.customers.append(c)
        events.append(("customer_arrived", {"customer_id": cid, "table_id": c["table_id"], "dish": dish}))

    def _leave(self, c, events):
        self.customers.remove(c)  # nhả giữ chỗ (reserved đi theo khách)
        self._set_reputation(self.t["left_reputation_delta"])
        events.append(("customer_left", {"customer_id": c["id"], "reputation": self.reputation}))

    def _pay(self, c, events):
        price = self.menu[c["dish"]]["price"]
        tip = c.get("tip", 0)
        self.money += price + tip
        self.earned += price + tip
        self.shift_earned += price + tip
        if tip > 0:
            self._set_reputation(self.t["tip_reputation"])
        self.customers.remove(c)
        events.append(("paid", {"customer_id": c["id"], "dish": c["dish"], "price": price, "tip": tip,
                                "money": self.money, "reputation": self.reputation}))

    def _interact(self, events):
        """Chọn đối tượng gần nhất trong interact_radius theo (khoảng cách, bếp trước bàn, id)."""
        r = self.t["interact_radius"]
        cands = [(math.dist(self.pos, o["pos"]), kind, id_key(o["id"]), o)
                 for kind, objs in ((0, self.stoves), (1, self.tables)) for o in objs
                 if math.dist(self.pos, o["pos"]) <= r]
        if not cands:
            return
        _, kind, _, obj = min(cands, key=lambda x: x[:3])
        if kind == 0:
            self._use_stove(obj, events)
        else:
            self._use_table(obj, events)

    def _use_stove(self, s, events):
        if s["state"] == "ready" and self.hand is None:
            self.hand = s["dish"]
            events.append(("dish_picked", {"stove_id": s["id"], "dish": s["dish"]}))
            s.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        elif s["state"] == "idle":
            waiting = [c for c in sort_by_id(self.customers) if c["state"] == "assigned" and not c["cooking"]]
            if not waiting:
                return
            c = waiting[0]  # khách đến trước (id nhỏ) được nấu trước
            for k, n in self.menu[c["dish"]]["recipe"].items():
                self.stock[k] -= n
            c["reserved"], c["cooking"] = {}, True
            s.update(state="cooking", dish=c["dish"], ready_ticks=0,
                     cook_ticks_left=int(round(self.menu[c["dish"]]["cook_s"] * TICK)))
            events.append(("cook_started", {"stove_id": s["id"], "dish": c["dish"], "customer_id": c["id"]}))

    def _use_table(self, tb, events):
        c = next((c for c in self.customers if c["table_id"] == tb["id"]), None)
        if c is None or self.hand is None or c["state"] != "assigned" or c["dish"] != self.hand:
            return
        c.update(state="eating", eat_ticks_left=int(round(self.t["eat_s"] * TICK)),
                 tip=self._tip_for(c["dish"], c["patience_ticks"]))
        events.append(("served", {"customer_id": c["id"], "dish": self.hand, "table_id": tb["id"]}))
        self.hand = None

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t["ramp_max_ticks"]))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])

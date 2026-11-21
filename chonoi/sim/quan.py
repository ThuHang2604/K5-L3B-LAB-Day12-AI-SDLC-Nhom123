"""Buổi tối — Mở Quán (`quan`), Test Contract mục F "Quán".

Thứ tự một bước:
  1. đồng hồ, timer ca, nấu, ăn, kiên nhẫn (ready_ticks chỉ tăng cho món đã ready ở đầu bước)
  2. bếp theo id: nấu xong -> ready (dish_ready)
  3. di chuyển, tối đa MỘT interact chọn theo (khoảng cách, bếp trước bàn, id)
  4. theo id bàn: khách ăn xong trả tiền (paid) và rời; còn giờ: khách hết kiên nhẫn rời (customer_left)
     hết ca: khách đang ăn trả ngay (closing), khách chờ rời (closing, không trừ uy tín), rồi quan_end
  5. còn giờ: lượt khách theo lịch (customer_arrived / no_dish)

Kho `stock` là tồn VẬT LÝ, gồm cả phần khách đang giữ (`reserved`). Kho khả dụng = stock − tổng reserved.
"""

import math

from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


def ticks(seconds):
    return int(round(seconds * TICK))


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, menu_ids=None,
                 money=0, earned=0, reputation=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        # Danh sách món khách có thể gọi (mode day lọc theo kế hoạch), sắp theo mã Unicode
        self.menu_ids = sorted(menu_ids if menu_ids is not None else self.menu.keys())
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.duration = ticks(t["duration_s"])
        self.time_left_ticks = scenario.get("time_left_ticks", self.duration)
        if reputation is None:
            reputation = scenario.get("reputation", t["reputation_initial"])
        self.reputation = reputation
        self.random_customers = scenario.get("random_customers", True)
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.patience_full = ticks(t["patience_s"])
        self.customers = []
        for c in scenario.get("customers", []):
            cu = {"id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                  "order_tick": c.get("order_tick", 0), "state": c.get("state", "waiting"),
                  "patience_ticks_left": c.get("patience_ticks_left", self.patience_full),
                  "eat_ticks_left": c.get("eat_ticks_left", 0),
                  "order_status": c.get("order_status", "reserved"),
                  "reserved": dict(c["reserved"]) if "reserved" in c else None,
                  "base_price": c.get("base_price"), "tip": c.get("tip")}
            self.customers.append(cu)
            ids.reserve(cu["id"])
        # Thiếu reserved ở đơn reserved: cấp theo công thức, thứ tự (order_tick, id bàn)
        for cu in sorted(self.customers, key=lambda c: (c["order_tick"], id_key(c["table_id"]))):
            if cu["reserved"] is None:
                cu["reserved"] = dict(self.menu[cu["dish_id"]]["recipe"]) if cu["order_status"] == "reserved" else {}
        self.money = money
        self.earned = earned
        self.shift_earned = 0
        self.phase_tick = 0
        self.done = False
        self.reason = None
        validate_state(self)

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    # --- kho ----------------------------------------------------------------------
    def reserved_total(self) -> dict:
        tot = {}
        for c in self.customers:
            for k, v in (c.get("reserved") or {}).items():
                tot[k] = tot.get(k, 0) + v
        return tot

    def available(self) -> dict:
        res = self.reserved_total()
        return {k: self.stock.get(k, 0) - res.get(k, 0) for k in self.stock}

    def _can_make(self, dish_id, avail) -> bool:
        return all(avail.get(k, 0) >= v for k, v in self.menu[dish_id]["recipe"].items())

    # --- snapshot -------------------------------------------------------------------
    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": [dict(c, reserved={k: c["reserved"][k] for k in sorted(c["reserved"])})
                          for c in sort_by_id(self.customers)],
        }

    # --- một bước -----------------------------------------------------------------
    def step(self, inp):
        events = []
        self.phase_tick += 1
        # 1. đồng hồ và các timer
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        ready_at_start = [s for s in self.stoves if s["state"] == "ready"]
        for s in self.stoves:
            if s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
        for s in ready_at_start:
            s["ready_ticks"] += 1
        for c in self.customers:
            if c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
            else:
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)
        # 2. bếp nấu xong
        for s in self.stoves:
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"], s["ready_ticks"] = "ready", 0
                events.append(("dish_ready", {"stove_id": s["id"], "order_id": s["dish"]["order_id"],
                                              "dish_id": s["dish"]["dish_id"]}))
        # 3. di chuyển rồi tối đa một interact
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        # 4. thanh toán / rời bàn
        closing = self.time_left_ticks <= 0
        for tb in self.tables:
            c = self._customer_at(tb["id"])
            if c is None:
                continue
            if c["state"] == "eating" and (c["eat_ticks_left"] == 0 or closing):
                self._pay(c, "finished_eating" if c["eat_ticks_left"] == 0 else "closing", events)
            elif c["state"] == "waiting" and closing:
                self._leave(c, "closing", events)
            elif c["state"] == "waiting" and c["patience_ticks_left"] == 0:
                self._leave(c, "patience", events)
        if closing:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
            return events
        # 5. khách mới theo lịch
        if self.random_customers and self._arrival_due():
            self._spawn_customer(events)
        return events

    # --- luật ----------------------------------------------------------------------
    def _arrival_due(self) -> bool:
        first = self.t["first_customer_tick"]
        interval = ticks(self.t["customer_interval_s"])
        pt = self.phase_tick
        return pt >= first and (pt - first) % interval == 0

    def _customer_at(self, table_id):
        for c in self.customers:
            if c["table_id"] == table_id:
                return c
        return None

    def _spawn_customer(self, events):
        taken = {c["table_id"] for c in self.customers}
        free = [tb for tb in self.tables if tb["id"] not in taken]
        if not free:
            return
        table = free[0]
        avail = self.available()
        options = [d for d in self.menu_ids if self._can_make(d, avail)]
        if not options:
            events.append(("no_dish", {}))
            return
        dish_id = options[self.rng.get("customers").randrange(len(options))]
        cid = self.ids.new("C")
        self.customers.append({
            "id": cid, "table_id": table["id"], "dish_id": dish_id, "order_tick": self.phase_tick,
            "state": "waiting", "patience_ticks_left": self.patience_full, "eat_ticks_left": 0,
            "order_status": "reserved", "reserved": dict(self.menu[dish_id]["recipe"]),
            "base_price": None, "tip": None})
        events.append(("customer_arrived", {"order_id": cid, "table_id": table["id"], "dish_id": dish_id}))

    def _interact(self, events):
        r = self.t["interact_radius"]
        cands = []
        for s in self.stoves:
            dd = math.dist(self.pos, s["pos"])
            if dd <= r:
                cands.append(((dd, 0, id_key(s["id"])), "stove", s))
        for tb in self.tables:
            dd = math.dist(self.pos, tb["pos"])
            if dd <= r:
                cands.append(((dd, 1, id_key(tb["id"])), "table", tb))
        if not cands:
            return
        _, kind, obj = min(cands, key=lambda c: c[0])
        if kind == "stove":
            if obj["state"] == "idle":
                self._start_cooking(obj, events)
            elif obj["state"] == "ready" and self.hand is None:
                self.hand = obj["dish"]
                events.append(("dish_picked", {"stove_id": obj["id"], "order_id": obj["dish"]["order_id"],
                                               "dish_id": obj["dish"]["dish_id"]}))
                obj.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        else:
            c = self._customer_at(obj["id"])
            if c and c["state"] == "waiting" and self.hand and self.hand["order_id"] == c["id"]:
                self._serve(c, events)

    def _start_cooking(self, stove, events):
        orders = [c for c in self.customers if c["state"] == "waiting" and c["order_status"] == "reserved"]
        if not orders:
            return
        c = min(orders, key=lambda c: (c["order_tick"], id_key(c["table_id"])))
        dish = self.menu[c["dish_id"]]
        items = []
        for k in sorted(c["reserved"]):
            self.stock[k] = self.stock.get(k, 0) - c["reserved"][k]
            items.extend([k] * c["reserved"][k])
        c["reserved"] = {}
        c["order_status"] = "assigned"
        c["base_price"] = dish["price"]
        payload = {"order_id": c["id"], "dish_id": c["dish_id"], "base_price": dish["price"]}
        stove.update(state="cooking", dish=payload, cook_ticks_left=ticks(dish["cook_s"]), ready_ticks=0)
        events.append(("cook_started", {"stove_id": stove["id"], "order_id": c["id"], "dish_id": c["dish_id"],
                                        "items": items, "base_price": dish["price"]}))

    def _serve(self, c, events):
        base = self.hand["base_price"]
        ratio = c["patience_ticks_left"] / self.patience_full
        tip = math.floor(base * self.t["tip_rate"]) if ratio >= self.t["tip_min_patience_ratio"] else 0
        c.update(state="eating", eat_ticks_left=ticks(self.t["eat_s"]), order_status="served",
                 base_price=base, tip=tip)
        self.hand = None
        events.append(("served", {"order_id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                                  "patience_ticks_left": c["patience_ticks_left"], "base_price": base, "tip": tip}))

    def _clamp_rep(self, v):
        return min(self.t["reputation_max"], max(self.t["reputation_min"], v))

    def _pay(self, c, reason, events):
        amount = c["base_price"] + c["tip"]
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if c["tip"] > 0:
            self.reputation = self._clamp_rep(self.reputation + self.t["tip_reputation"])
        events.append(("paid", {"order_id": c["id"], "table_id": c["table_id"], "base_price": c["base_price"],
                                "tip": c["tip"], "amount": amount, "reason": reason}))
        self.customers.remove(c)

    def _leave(self, c, reason, events):
        if reason == "patience":
            self.reputation = self._clamp_rep(self.reputation + self.t["left_reputation_delta"])
        # nhả phần giữ (bỏ khách là đủ), bỏ món của đơn ở bếp/tay; nguyên liệu đã dùng không hoàn lại
        for s in self.stoves:
            if s["dish"] and s["dish"]["order_id"] == c["id"]:
                s.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        if self.hand and self.hand["order_id"] == c["id"]:
            self.hand = None
        self.customers.remove(c)
        events.append(("customer_left", {"order_id": c["id"], "table_id": c["table_id"], "reason": reason,
                                         "reputation": self.reputation}))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])


# --- kiểm mâu thuẫn trạng thái dựng từ scenario (mã 2) ------------------------------
def validate_state(sim):
    from ..errors import BadInput
    menu = sim.menu
    by_id = {c["id"]: c for c in sim.customers}
    stove_orders = {}
    for s in sim.stoves:
        st, dish = s["state"], s.get("dish")
        if st not in ("idle", "cooking", "ready"):
            raise BadInput(f"bếp {s['id']}: state không hợp lệ")
        for k in ("cook_ticks_left", "ready_ticks"):
            v = s.get(k)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise BadInput(f"bếp {s['id']}: {k} phải là số nguyên không âm")
        if st == "idle":
            if dish is not None or s["cook_ticks_left"] or s["ready_ticks"]:
                raise BadInput(f"bếp {s['id']}: idle không có món/bộ đếm")
            continue
        _check_payload(dish, f"bếp {s['id']}", menu)
        if st == "cooking" and (s["cook_ticks_left"] <= 0 or s["ready_ticks"]):
            raise BadInput(f"bếp {s['id']}: cooking cần cook_ticks_left > 0")
        if st == "ready" and s["cook_ticks_left"]:
            raise BadInput(f"bếp {s['id']}: ready không còn thời gian nấu")
        if dish["order_id"] in stove_orders:
            raise BadInput("hai bếp giữ cùng đơn")
        stove_orders[dish["order_id"]] = s
    held = {}
    if sim.hand is not None:
        _check_payload(sim.hand, "hand", menu)
        held[sim.hand["order_id"]] = sim.hand
        if sim.hand["order_id"] in stove_orders:
            raise BadInput("bếp và tay giữ cùng đơn")
    for oid, payload in list(held.items()) + [(o, s["dish"]) for o, s in stove_orders.items()]:
        c = by_id.get(oid)
        if c is None:
            raise BadInput(f"món của đơn {oid} không có khách")
        if c["order_status"] != "assigned" or c["state"] != "waiting":
            raise BadInput(f"món của đơn {oid} nhưng đơn không ở trạng thái assigned")
        if payload["dish_id"] != c["dish_id"] or payload["base_price"] != menu[c["dish_id"]]["price"]:
            raise BadInput(f"món không khớp đơn {oid}")
    for c in sim.customers:
        oid, status, state = c["id"], c["order_status"], c["state"]
        has_dish = oid in held or oid in stove_orders
        if state == "waiting":
            if status == "served":
                raise BadInput(f"khách {oid}: waiting không thể là served")
            if c["eat_ticks_left"]:
                raise BadInput(f"khách {oid}: waiting không có timer ăn")
            if status == "assigned" and not has_dish:
                raise BadInput(f"khách {oid}: assigned cần đúng một món ở bếp hoặc tay")
            if status in ("reserved", "unfulfillable") and has_dish:
                raise BadInput(f"khách {oid}: {status} không có món")
            if status == "reserved" and c["reserved"] != menu[c["dish_id"]]["recipe"]:
                raise BadInput(f"khách {oid}: giữ khác công thức")
            if status != "reserved" and c["reserved"]:
                raise BadInput(f"khách {oid}: {status} phải có giữ chỗ rỗng")
        else:  # eating
            if status != "served" or c["eat_ticks_left"] <= 0 or has_dish or c["reserved"]:
                raise BadInput(f"khách {oid}: eating cần served, timer ăn dương, không giữ/không món")
            if not isinstance(c["base_price"], int) or not isinstance(c["tip"], int):
                raise BadInput(f"khách {oid}: eating phải khai base_price và tip đã chốt")
    res = sim.reserved_total()
    for k, v in res.items():
        if v > sim.stock.get(k, 0):
            raise BadInput(f"giữ chỗ {k} vượt tồn kho")


def _check_payload(p, where, menu):
    from ..errors import BadInput
    if (not isinstance(p, dict) or set(p) != {"order_id", "dish_id", "base_price"}
            or not isinstance(p["order_id"], str) or p["dish_id"] not in menu):
        raise BadInput(f"{where}: payload món phải là {{order_id,dish_id,base_price}} hợp lệ")

"""Vòng ngày (`--mode day`, Test Contract v1.1): DayIntro -> gather -> quan -> Shop -> Ngày kế.

Headless chỉ có ba pha gameplay `gather`, `quan`, `shop`; các màn DayIntro/EveningIntro/DayResult/Summary là UI.
Đổi pha (mục 4.5): day_start -> day_plan -> phase_start(gather). Sau gather_end dựng quán và phát
phase_start(quan) cùng tick (kể cả khi ngất). Sau quan_end dựng Shop và phát phase_start(shop) cùng tick.
Pha mới chạy gameplay từ bước sau. Đóng Shop tăng days_completed; chỉ khi dựng Ngày mới mới sao cấp đã mua
sang active_upgrades.

Tiền, earned, uy tín và cấp nâng cấp giữ qua Ngày; oxy/Máu hồi đầy theo cấp đang áp dụng; giỏ làm mới;
kho dư bị bỏ sau Shop.
"""

import copy

from .. import fresh as fr
from ..contract import plan_ingredients
from .gather import GatherSim
from .quan import QuanSim


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.rng = streams
        self.ids = ids
        self.days = days
        self.g_tpl = scenario.get("gather", {})
        for it in self.g_tpl.get("hold", []):
            ids.reserve(it["id"])
        self.q_tpl = scenario.get("quan", {})
        d = scenario.get("day", {})
        self.money = d.get("money", 0)
        self.earned = d.get("earned", 0)
        self.reputation = d.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = dict(d.get("upgrades", {}))  # cấp đã mua
        self.active_upgrades = dict(self.upgrades)  # cấp đang áp dụng
        self.plans = {p["day"]: {"dishes": dict(p["dishes"]), "ingredients": dict(p["ingredients"])}
                      for p in tuning["day_plan"]}
        for p in d.get("day_plan", []):
            self.plans[p["day"]] = {"dishes": dict(p["dishes"]),
                                    "ingredients": plan_ingredients(p["dishes"], tuning["menu"])}
        self.shop_t = tuning["shop"]
        self.day = 0
        self.days_completed = 0
        self.done = False
        self.reason = None
        self.sub = None
        self.phase = "gather"
        self.shop_stock = {}
        self.shop_time_left = 0
        self.shop_tick = 0
        self.initial_events = []
        self._new_day(self.initial_events)

    # --- trạng thái chung cho snapshot ------------------------------------------------
    @property
    def phase_tick(self):
        return self.shop_tick if self.phase == "shop" else self.sub.phase_tick

    @property
    def time_left_ticks(self):
        return self.shop_time_left if self.phase == "shop" else self.sub.time_left_ticks

    def plan_day(self):
        """Kế hoạch D1–D5 lặp lại từ Ngày 6 (soak 10 Ngày, TICKET-04)."""
        return (self.day - 1) % len(self.plans) + 1

    def plan(self):
        p = self.plans[self.plan_day()]
        return {"dishes": {k: p["dishes"][k] for k in sorted(p["dishes"])},
                "ingredients": {k: p["ingredients"][k] for k in sorted(p["ingredients"])}}

    def snapshot(self) -> dict:
        body = {"day": self.day, "day_plan": self.plan(),
                "upgrades": {k: self.upgrades[k] for k in sorted(self.upgrades)},
                "active_upgrades": {k: self.active_upgrades[k] for k in sorted(self.active_upgrades)},
                "days_completed": self.days_completed}
        if self.phase == "shop":
            body["stock"] = list(self.shop_stock)
            body["shop"] = {"money": self.money, "levels": self._levels_info()}
        else:
            body.update(self.sub.snapshot())
        return body

    def _levels_info(self):
        out = {}
        for uid, levels in self.shop_t["upgrades"].items():
            cur = self.upgrades.get(uid, 0)
            nxt = levels[cur] if cur < len(levels) else None
            out[uid] = {"level": cur, "max_level": len(levels), "next_price": nxt["price"] if nxt else None}
        return out

    # --- dựng pha ---------------------------------------------------------------------
    def _effective(self, uid, field, base):
        lv = self.active_upgrades.get(uid, 0)
        return self.shop_t["upgrades"][uid][lv - 1][field] if lv > 0 else base

    def _new_day(self, events):
        self.day += 1
        self.active_upgrades = dict(self.upgrades)
        g = self.tuning["gather"]
        # Ngày đầu giữ nguyên id trong mẫu gather.hold; Ngày kế cấp id mới theo thứ tự mảng
        hold = None if self.day == 1 else [{"id": self.ids.new("I"), "kind": it["kind"], "fresh": it["fresh"]}
                                           for it in self.g_tpl.get("hold", [])]
        self.sub = GatherSim(self.tuning, copy.deepcopy(self.g_tpl), self.rng, self.ids, day=self.day, hold_items=hold,
                             oxygen_max_s=self._effective("oxygen", "oxygen_max_s", g["oxygen_max_s"]),
                             hp_max=self._effective("hp", "hp_max", g["hp_max"]),
                             money=self.money, earned=self.earned, reputation=self.reputation)
        self.phase = "gather"
        events.append(("day_start", {}, "gather"))
        events.append(("day_plan", self.plan(), "gather"))
        events.append(("phase_start", {}, "gather"))

    def _open_quan(self, inventory, events):
        self.sub = QuanSim(self.tuning, copy.deepcopy(self.q_tpl), self.rng, self.ids, inventory=inventory,
                           menu_ids=list(self.plans[self.plan_day()]["dishes"]), money=self.money, earned=self.earned,
                           reputation=self.reputation)
        self.phase = "quan"
        events.append(("phase_start", {}, "quan"))

    def _open_shop(self, events):
        self.shop_stock = fr.export_sorted(self.sub.stock.values())  # hàng thô ở Shop không hao tươi
        self.shop_time_left = self.shop_t["max_ticks"]
        self.shop_tick = 0
        self.phase = "shop"
        events.append(("phase_start", {}, "shop"))

    # --- một bước gameplay --------------------------------------------------------------
    def step(self, inp):
        out = []
        if self.phase == "gather":
            for name, data in self.sub.step(inp):
                out.append((name, data, "gather"))
            if self.sub.done:
                self._open_quan(self.sub.inventory_items(), out)
        elif self.phase == "quan":
            for name, data in self.sub.step(inp):
                out.append((name, data, "quan"))
            self.money, self.earned, self.reputation = self.sub.money, self.sub.earned, self.sub.reputation
            if self.sub.done:
                self._open_shop(out)
        else:
            self._shop_step(inp, out)
        return out

    def _shop_step(self, inp, out):
        self.shop_tick += 1
        self.shop_time_left = max(0, self.shop_time_left - 1)
        if inp.buy is not None:
            self._buy(inp.buy, out)
        if inp.pressed("shop_done"):
            out.append(("shop_end", {"reason": "done"}, "shop"))
        elif self.shop_time_left <= 0:
            out.append(("shop_end", {"reason": "time"}, "shop"))
        else:
            return
        self.days_completed += 1
        if self.days_completed >= self.days:
            self.done = True
            self.reason = "days_complete"
        else:
            self._new_day(out)

    def _buy(self, action, out):
        levels = self.shop_t["upgrades"].get(action)
        if levels is None:
            out.append(("buy_failed", {"action": action, "reason": "unknown"}, "shop"))
            return
        cur = self.upgrades.get(action, 0)
        if cur >= len(levels):
            out.append(("buy_failed", {"action": action, "reason": "max_level"}, "shop"))
            return
        price = levels[cur]["price"]
        if self.money < price:
            out.append(("buy_failed", {"action": action, "reason": "funds"}, "shop"))
            return
        self.money -= price
        self.upgrades[action] = cur + 1
        out.append(("bought", {"upgrade": action, "level": cur + 1, "price": price, "money": self.money}, "shop"))

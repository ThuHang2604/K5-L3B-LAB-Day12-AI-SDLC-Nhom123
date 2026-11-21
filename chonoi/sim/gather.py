"""Buổi sáng — Lặn & Hái (`gather`), Test Contract v1.0 mục F "Gather" + v1.1 mục 4.5.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Thứ tự một bước:
  1. đồng hồ, hồi bắt, hồi nút (node_regrown)
  2. bơi + chặn mép -> dive/surface -> oxy theo d cuối bước -> oxygen_empty -> ngạt (choke) -> ngất (faint)
  3. cạnh interact: bến trước (docked), ngoài bến chỉ hái khi ở mặt nước (gather / hold_full)
  4. cạnh catch: hết hồi + dưới nước -> đàn gần nhất trong bán kính (fish_caught / hold_full)
  5. hết giờ -> gather_end(time)
v1.1: sau bước 2 cập nhật Cá Sấu theo id rồi xét tối đa một hit; nếu còn giờ, cá bơi rồi sinh theo lịch.
v1.2: giỏ là cá thể {id,kind,fresh}; bước 1 hao tươi hàng có sẵn (2 đơn vị/tick) và phát spoiled theo id;
hàng mới fresh 100, hao từ bước sau; mất hàng (hit/ngất) theo LIFO dạng mảng cá thể.
"""

import math

from ..ids import id_key, sort_by_id
from .. import fresh as fr
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


def ticks(seconds):
    return int(round(seconds * TICK))


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, oxygen_max_s=None, hp_max=None,
                 money=0, earned=0, reputation=None, hold_items=None):
        t = tuning["gather"]
        self.tuning = tuning
        self.decay = fr.per_tick_units(tuning["freshness"]["gather_decay_per_s"])
        self.thr = fr.threshold(tuning)
        self.t = t
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = ticks(oxygen_max_s if oxygen_max_s is not None else t["oxygen_max_s"])
        self.hp_max = hp_max if hp_max is not None else t["hp_max"]
        self.mon = t["monsters"]
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        from ..errors import BadInput
        if self.oxygen_ticks > self.oxygen_max or not (1 <= self.hp <= self.hp_max):
            raise BadInput("player.oxygen_ticks / hp vượt mức tối đa đang áp dụng")
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        # giỏ: cá thể theo thứ tự vào giỏ (cuối mảng là mới nhất). day truyền hold_items đã cấp id cho Ngày kế
        self.hold = fr.from_json(hold_items if hold_items is not None else scenario.get("hold", []))
        for it in self.hold:
            ids.reserve(it["id"])
        self.time_left_ticks = scenario.get("time_left_ticks", ticks(t["duration_s"]))
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        self.phase_tick = 0
        self.fish_active = scenario.get("random_fish", True)  # false: cá fixture đứng yên, không sinh
        if "fish" in scenario:
            self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                          "heading_deg": float(f.get("heading_deg", 0)), "age_ticks": f.get("age_ticks", 0)}
                         for f in scenario["fish"]]
        else:
            self.fish = []
        for coll in (self.nodes, self.fish):
            for e in coll:
                ids.reserve(e["id"])
        if "fish" not in scenario and self.fish_active:
            for _ in range(t["fish_initial"]):
                self._spawn_fish(streams.get("fish_init"), None)
        if "monsters" in scenario:
            src_m = scenario["monsters"]
        else:
            src_m = [dict(m, pos=list(m["waypoints"][0])) for m in self.mon["spawns"] if m["from_day"] <= day]
        self.monsters = sort_by_id([{
            "id": m["id"], "kind": m["kind"], "pos": [float(c) for c in m["pos"]],
            "waypoints": [[float(c) for c in w] for w in m["waypoints"]],
            "target_idx": m.get("target_idx", 1), "state": m.get("state", "patrol"),
            "state_ticks_left": m.get("state_ticks_left", 0), "recoil_dir": m.get("recoil_dir")} for m in src_m])
        self.money = money
        self.earned = earned
        self.reputation = reputation if reputation is not None else tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> list:
        return fr.export_sorted(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.hp_max, "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": [fr.export(i) for i in self.hold], "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "kind": n["kind"], "pos": n["pos"],
                       "regrow_ticks": n["regrow_ticks"], "ready": n["regrow_ticks"] == 0}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "kind": f["kind"], "pos": f["pos"], "heading_deg": f["heading_deg"],
                      "age_ticks": f["age_ticks"]} for f in sort_by_id(self.fish)],
            "monsters": [{k: m[k] for k in ("id", "kind", "pos", "waypoints", "target_idx", "state",
                                             "state_ticks_left", "recoil_dir")} for m in self.monsters],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.phase_tick += 1
        # 1. đồng hồ, hồi bắt, bất tử, hồi nút
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        fr.decay(self.hold, self.decay, self.thr, "hold", events)
        # 2. bơi, dive/surface, oxy, ngạt
        was_surface = self._at_surface()
        self._move(inp)
        now_surface = self._at_surface()
        if was_surface and not now_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif now_surface and not was_surface:
            events.append(("surface", {"pos": list(self.pos)}))
        if self._oxygen(events):
            return events
        # 2b. Cá Sấu theo id, rồi tối đa một hit
        if self._monsters(events):
            return events
        # 3. interact: bến trước, rồi hái (chỉ ở mặt nước)
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if now_surface:
                self._harvest(events)
        # 4. bắt cá
        if inp.pressed("catch"):
            self._catch(events)
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        # 6. còn giờ: cá bơi, rồi sinh thêm theo lịch
        if self.fish_active:
            self._swim_fish()
            if self.phase_tick % self.t["fish_spawn_ticks"] == 0 and len(self.fish) < self.t["fish_max"]:
                self._spawn_fish(self.rng.get("fish_spawn"), events)
        return events

    # --- luật ----------------------------------------------------------------------
    def _oxygen(self, events) -> bool:
        """Oxy theo d cuối bước. Trả True nếu ngất (đã phát faint + gather_end)."""
        if self._at_surface():
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"])
            self.zero_oxy_ticks = 0
            return False
        before = self.oxygen_ticks
        self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
        if before > 0 and self.oxygen_ticks == 0:
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        if self.oxygen_ticks == 0:
            self.zero_oxy_ticks += 1
            if self.zero_oxy_ticks >= self.t["choke_interval_ticks"]:
                self.zero_oxy_ticks = 0
                self.hp -= 1
                events.append(("choke", {"hp": self.hp}))
                if self.hp <= 0:
                    self._faint("choke", events)
                    return True
        return False

    # --- cá bơi / sinh --------------------------------------------------------------
    def _swim_fish(self):
        t = self.t
        step = t["fish_speed"] / TICK
        xlo, xhi = t["fish_x"]
        turn = self.rng.get("fish_turn")
        for f in sort_by_id(self.fish):
            if (f["age_ticks"] + 1) % t["fish_turn_ticks"] == 0:
                f["heading_deg"] = turn.uniform(0, 360)
            dlo, dhi = t["fish_depths"][f["kind"]]
            h = math.radians(f["heading_deg"])
            vx, vd = math.cos(h), math.sin(h)
            x, d = f["pos"]
            x, d = min(max(x, xlo), xhi), min(max(d, dlo), dhi)
            x, vx = _reflect(x + vx * step, vx, xlo, xhi)
            d, vd = _reflect(d + vd * step, vd, dlo, dhi)
            f["pos"] = [x, d]
            f["heading_deg"] = math.degrees(math.atan2(vd, vx)) % 360
            f["age_ticks"] += 1

    def _spawn_fish(self, rng, events):
        """Chọn loài theo trọng số (chuẩn hóa trên loài còn điểm hợp lệ), rồi điểm đều, rồi hướng theo seed."""
        t = self.t
        clear = t["fish_spawn_clearance"]
        options = {}
        for kind in sorted(t["fish_spawn_depths"]):
            pts = [(float(x), float(d)) for x in t["fish_spawn_x"] for d in t["fish_spawn_depths"][kind]
                   if all(math.dist((x, d), f["pos"]) > clear for f in self.fish)]
            if pts:
                options[kind] = pts
        if not options:
            return None
        total = sum(t["fish_weights"][k] for k in options)
        r = rng.random() * total
        kind = None
        for k in options:
            kind = k
            r -= t["fish_weights"][k]
            if r < 0:
                break
        pts = options[kind]
        pos = list(pts[rng.randrange(len(pts))])
        f = {"id": self.ids.new("F"), "kind": kind, "pos": pos, "heading_deg": rng.uniform(0, 360), "age_ticks": 0}
        self.fish.append(f)
        if events is not None:
            events.append(("fish_spawned", {"id": f["id"], "kind": kind, "pos": list(pos)}))
        return f

    # --- Cá Sấu ---------------------------------------------------------------------
    def _monsters(self, events) -> bool:
        if not self.monsters:
            return False
        b = self.t["bounds"]
        skip = set()
        for m in self.monsters:
            sp = self.mon["species"][m["kind"]]
            thr = sp["depths"][0]
            deep = self.pos[1] >= thr
            if m["state"] == "recoil":
                k = sp["recoil_dist"] / sp["recoil_ticks"]
                m["pos"] = [m["pos"][0] + m["recoil_dir"][0] * k, m["pos"][1] + m["recoil_dir"][1] * k]
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m.update(state="patrol", state_ticks_left=0, recoil_dir=None)
                    skip.add(m["id"])
            else:
                dist = math.dist(m["pos"], self.pos)
                if m["state"] == "patrol" and deep and dist <= sp["detect_radius"]:
                    m["state"] = "chase"
                elif m["state"] == "chase" and (dist > sp["exit_radius"] or not deep):
                    m["state"] = "patrol"
                if m["state"] == "chase":
                    m["pos"] = _toward(m["pos"], self.pos, sp["chase_speed"] / TICK)
                else:
                    tgt = m["waypoints"][m["target_idx"]]
                    m["pos"] = _toward(m["pos"], tgt, sp["patrol_speed"] / TICK)
                    if m["pos"] == [float(tgt[0]), float(tgt[1])]:
                        m["target_idx"] = 1 - m["target_idx"]
            lo, hi = sp["depths"]
            m["pos"] = [min(max(m["pos"][0], b["x"][0]), b["x"][1]), min(max(m["pos"][1], lo), hi)]
        if self.invuln_ticks > 0:
            return False
        best = None
        for m in self.monsters:
            sp = self.mon["species"][m["kind"]]
            if m["state"] == "recoil" or m["id"] in skip or self.pos[1] < sp["depths"][0]:
                continue
            dd = math.dist(m["pos"], self.pos)
            if dd <= sp["hit_radius"]:
                key = (dd, id_key(m["id"]))
                if best is None or key < best[0]:
                    best = (key, m)
        if best is None:
            return False
        m = best[1]
        sp = self.mon["species"][m["kind"]]
        self.hp -= 1
        n_lost = math.floor(len(self.hold) * self.mon["loss_ratio"])
        lost = [fr.export(self.hold.pop()) for _ in range(n_lost)]
        self.invuln_ticks = self.mon["invuln_ticks"]
        dx, dd = m["pos"][0] - self.pos[0], m["pos"][1] - self.pos[1]
        n = math.hypot(dx, dd)
        m.update(state="recoil", state_ticks_left=sp["recoil_ticks"],
                 recoil_dir=[dx / n, dd / n] if n > 0 else [1.0, 0.0])
        events.append(("monster_hit", {"monster_id": m["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        if self.hp <= 0:
            self._faint("monster", events)
            return True
        return False

    def _faint(self, cause, events):
        self.hp = 0
        lost = [fr.export(i) for i in reversed(self.hold)]  # LIFO: vào giỏ sau bỏ trước
        self.hold = []
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)

    def _free(self):
        return self.t["hold_capacity"] - len(self.hold)

    def _nearest(self, items, radius):
        best = None
        for e in items:
            dd = math.dist(self.pos, e["pos"])
            if dd <= radius:
                k = (dd, id_key(e["id"]))
                if best is None or k < best[0]:
                    best = (k, e)
        return best[1] if best else None

    def _harvest(self, events):
        ready = [n for n in self.nodes if n["regrow_ticks"] == 0]
        n = self._nearest(ready, self.t["interact_radius"])
        if n is None:
            return
        amount = self.t["node_yield"]
        free = self._free()
        if free < amount:
            events.append(("hold_full", {"action": "gather", "node_id": n["id"], "required": amount, "free": free}))
            return
        self.hold.extend(fr.new_item(self.ids, n["kind"], self.tuning) for _ in range(amount))
        n["regrow_ticks"] = ticks(self.t["regrow_s"])
        events.append(("gather", {"node_id": n["id"], "kind": n["kind"], "amount": amount}))

    def _catch(self, events):
        if self.catch_cd_ticks > 0 or self._at_surface():
            return
        f = self._nearest(self.fish, self.t["catch_radius"])
        if f is None:
            return
        y = self.t["fish_yield"][f["kind"]]
        free = self._free()
        if free < y:
            events.append(("hold_full", {"action": "catch", "fish_id": f["id"], "required": y, "free": free}))
            return
        self.hold.extend(fr.new_item(self.ids, f["kind"], self.tuning) for _ in range(y))
        self.fish.remove(f)
        events.append(("fish_caught", {"fish_id": f["id"], "kind": f["kind"], "yield": y}))
        self.catch_cd_ticks = ticks(self.t["catch_cooldown_s"])

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])


def _reflect(v, dirc, lo, hi):
    """Phản xạ phần quãng đường vượt mép và đảo thành phần hướng vuông góc với mép."""
    if v > hi:
        return 2 * hi - v, -abs(dirc)
    if v < lo:
        return 2 * lo - v, abs(dirc)
    return v, dirc


def _toward(pos, target, step):
    dx, dd = target[0] - pos[0], target[1] - pos[1]
    n = math.hypot(dx, dd)
    if n <= step + 1e-9:  # dung sai số thực: tới đích trong bước này
        return [float(target[0]), float(target[1])]
    return [pos[0] + dx / n * step, pos[1] + dd / n * step]

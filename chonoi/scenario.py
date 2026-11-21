"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
TODO(nhóm): bổ sung kiểm mâu thuẫn mức luật mà nhóm cần (khách giữ chỗ quá kho, đơn assigned
phải có đúng một món, khách eating thiếu giá/tip...) — xem PRD-0 mục D và 'Mâu thuẫn -> mã 2'.
"""

import json
import math

from .errors import BadInput
from .inventory import kinds_from_tuning, validate_instances

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks", "monsters"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
QUAN_PLAYER_KEYS = {"pos", "vel"}
FISH_KEYS = {"id", "kind", "pos", "heading_deg", "age_ticks"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
TABLE_KEYS = {"id", "pos"}
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left", "eat_ticks_left",
                 "order_status", "reserved", "base_price", "tip"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if not isinstance(data, dict):
        raise BadInput("scenario phải là object")
    allowed_blocks = {"gather", "quan", "day"} if mode == "day" else {mode}
    if set(data) - allowed_blocks:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận {sorted(allowed_blocks)}")
    if mode == "day":
        out = {}
        for blk in ("gather", "quan", "day"):
            if blk in data:
                if not isinstance(data[blk], dict):
                    raise BadInput(f"khối {blk} phải là object")
                out[blk] = data[blk]
        if "gather" in out:
            _validate_block("gather", out["gather"], tuning)
        if "quan" in out:
            for k in ("stock", "reputation"):
                if k in out["quan"]:
                    raise BadInput(f"quan.{k} bị cấm khi chạy day (dùng gather.hold / day.reputation)")
            _validate_block("quan", out["quan"], tuning)
        if "day" in out:
            _validate_day(out["day"], tuning)
        return out
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    _validate_block(mode, block, tuning)
    return block


def _validate_block(mode, block, tuning):
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)


DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


def _validate_day(d, tuning):
    from .contract import plan_ingredients
    if set(d) - DAY_KEYS:
        raise BadInput(f"trường lạ trong day: {sorted(set(d) - DAY_KEYS)}")
    for k in ("money", "earned"):
        if k in d:
            _nonneg_int(f"day.{k}", d[k])
    if d.get("money", 0) > 0 and "earned" not in d:
        raise BadInput("day: khai cả money và earned khi có tiền đầu kỳ")
    if d.get("money", 0) > d.get("earned", 0):
        raise BadInput("day: cần 0 ≤ money ≤ earned")
    q = tuning["quan"]
    if "reputation" in d and not (_num(d["reputation"]) and q["reputation_min"] <= d["reputation"] <= q["reputation_max"]):
        raise BadInput("day.reputation ngoài miền")
    ups = tuning["shop"]["upgrades"]
    u = d.get("upgrades", {})
    if not isinstance(u, dict):
        raise BadInput("day.upgrades phải là object")
    for k, v in u.items():
        if k not in ups:
            raise BadInput(f"day.upgrades: nâng cấp lạ {k}")
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= len(ups[k])):
            raise BadInput(f"day.upgrades.{k} phải trong [0, {len(ups[k])}]")
    dp = d.get("day_plan", [])
    if not isinstance(dp, list):
        raise BadInput("day.day_plan phải là mảng")
    seen = set()
    for p in dp:
        if not isinstance(p, dict) or set(p) - {"day", "dishes", "ingredients"} or "dishes" not in p:
            raise BadInput("day.day_plan: mỗi mục {day, dishes[, ingredients]}")
        if p.get("day") not in (1, 2, 3, 4, 5) or isinstance(p.get("day"), bool) or p["day"] in seen:
            raise BadInput("day.day_plan.day phải là 1..5, không trùng")
        seen.add(p["day"])
        if not isinstance(p["dishes"], dict) or not p["dishes"]:
            raise BadInput("day.day_plan.dishes phải là map không rỗng")
        want = plan_ingredients(p["dishes"], tuning["menu"])
        if "ingredients" in p and p["ingredients"] != want:
            raise BadInput(f"day.day_plan[{p['day']}].ingredients khác tổng công thức: {want}")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        validate_instances(h, kinds_from_tuning(tuning), "gather.hold")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    ups = tuning.get("shop", {}).get("upgrades", {})
    omax = int(round(max([g["oxygen_max_s"]] + [u["oxygen_max_s"] for u in ups.get("oxygen", [])]) * 60))
    hpmax = max([g["hp_max"]] + [u["hp_max"] for u in ups.get("hp", [])])
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= hpmax):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    node_kinds = sorted({n["kind"] for n in g["nodes"]})
    fish_kinds = sorted(g["fish_yield"])
    for n in b.get("nodes", []):
        if set(n) - {"id", "kind", "pos", "regrow_ticks"}:
            raise BadInput(f"nodes.{n['id']}: trường lạ")
        if n.get("kind") not in node_kinds:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {node_kinds}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if set(f) - FISH_KEYS:
            raise BadInput(f"fish.{f['id']}: trường lạ")
        if f.get("kind") not in fish_kinds:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {fish_kinds}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])
    species = g["monsters"]["species"]
    for m in b.get("monsters", []):
        mid = m["id"]
        if set(m) - MONSTER_KEYS:
            raise BadInput(f"monsters.{mid}: trường lạ")
        if m.get("kind") not in species:
            raise BadInput(f"monsters.{mid}: kind phải thuộc {sorted(species)}")
        lo, hi = species[m["kind"]]["depths"]
        mb = {"x": bounds["x"], "d": [lo, hi]}
        _pos(f"monsters.{mid}.pos", m.get("pos"), mb)
        wps = m.get("waypoints")
        if not (isinstance(wps, list) and len(wps) == 2):
            raise BadInput(f"monsters.{mid}: cần đúng 2 waypoint")
        for wp in wps:
            _pos(f"monsters.{mid}.waypoints", wp, mb)
        if m.get("target_idx", 1) not in (0, 1) or isinstance(m.get("target_idx"), bool):
            raise BadInput(f"monsters.{mid}.target_idx phải là 0 hoặc 1")
        st = m.get("state", "patrol")
        if st not in ("patrol", "chase", "recoil"):
            raise BadInput(f"monsters.{mid}.state không hợp lệ")
        _nonneg_int(f"monsters.{mid}.state_ticks_left", m.get("state_ticks_left", 0))
        rd = m.get("recoil_dir")
        if st == "recoil":
            if m.get("state_ticks_left", 0) <= 0:
                raise BadInput(f"monsters.{mid}: recoil cần state_ticks_left > 0")
            if not (isinstance(rd, list) and len(rd) == 2 and all(_num(c) for c in rd)
                    and abs(math.hypot(*rd) - 1) < 1e-6):
                raise BadInput(f"monsters.{mid}: recoil_dir phải là vector đơn vị")
        elif rd is not None or m.get("state_ticks_left", 0) != 0:
            raise BadInput(f"monsters.{mid}: chỉ recoil mới có recoil_dir/state_ticks_left")


def _validate_quan(b, tuning):
    q = tuning["quan"]
    menu = tuning["menu"]
    kinds = kinds_from_tuning(tuning)
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        validate_instances(b["stock"], kinds, "quan.stock")
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    if "reputation" in b:
        r = b["reputation"]
        if not _num(r) or not (q["reputation_min"] <= r <= q["reputation_max"]):
            raise BadInput("reputation ngoài miền")
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = q["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    for s in b.get("stoves", []):
        if set(s) - STOVE_KEYS:
            raise BadInput(f"stoves.{s['id']}: trường lạ")
        if "pos" in s:
            _pos(f"stoves.{s['id']}.pos", s["pos"], qb, axes=("x", "z"))
    for t in b.get("tables", []):
        if set(t) - TABLE_KEYS:
            raise BadInput(f"tables.{t['id']}: trường lạ")
        if "pos" in t:
            _pos(f"tables.{t['id']}.pos", t["pos"], qb, axes=("x", "z"))
    table_ids = [c.get("table_id") for c in b.get("customers", [])]
    known = {t["id"] for t in q["tables"]}
    patience = int(round(q["patience_s"] * 60))
    eat = int(round(q["eat_s"] * 60))
    for c in b.get("customers", []):
        cid = c["id"]
        if set(c) - CUSTOMER_KEYS:
            raise BadInput(f"customers.{cid}: trường lạ")
        if not isinstance(c.get("table_id"), str) or c["table_id"] not in known:
            raise BadInput(f"customers.{cid}: table_id phải là bàn có thật")
        if c.get("dish_id") not in menu:
            raise BadInput(f"customers.{cid}: dish_id phải là món trong thực đơn")
        if c.get("state", "waiting") not in ("waiting", "eating"):
            raise BadInput(f"customers.{cid}: state phải là waiting hoặc eating")
        if c.get("order_status", "reserved") not in ("reserved", "assigned", "unfulfillable", "served"):
            raise BadInput(f"customers.{cid}: order_status không hợp lệ")
        for k in ("order_tick", "patience_ticks_left", "eat_ticks_left"):
            if k in c:
                _nonneg_int(f"customers.{cid}.{k}", c[k])
        if c.get("patience_ticks_left", 0) > patience or c.get("eat_ticks_left", 0) > eat:
            raise BadInput(f"customers.{cid}: bộ đếm vượt giá trị đầy")
        for k in ("base_price", "tip"):
            if k in c and c[k] is not None:
                _nonneg_int(f"customers.{cid}.{k}", c[k])
        if "reserved" in c:
            r = c["reserved"]
            if not isinstance(r, list) or not all(isinstance(x, str) and x for x in r) or len(set(r)) != len(r):
                raise BadInput(f"customers.{cid}.reserved phải là mảng id cá thể (chuỗi, không trùng)")
    if len(table_ids) != len(set(table_ids)):
        raise BadInput("hai khách cùng bàn")

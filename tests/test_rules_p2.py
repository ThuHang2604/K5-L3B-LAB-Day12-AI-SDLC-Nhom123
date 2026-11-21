"""Test luật Phase 2 (Test Contract v1.1), hộp đen qua headless_cmd. Số đọc từ game.contract.json."""

import json
import math
import time
import unittest

from helpers import Workdir, events, frames, ids_of, items, kinds_of, read_jsonl, run_headless, snapshots, write_json


def contract():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)


def T():
    return contract()["tuning"]


def run(w, mode, scenario=None, inputs=None, ticks=10, every=1, seed=1, extra=(), expect=0):
    args = ["--mode", mode, "--seed", str(seed), "--ticks", str(ticks), "--out", w.path("o.jsonl"),
            "--snapshot-every", str(every), *extra]
    if scenario is not None:
        args += ["--scenario", write_json(w.path("sc.json"), scenario)]
    if inputs is not None:
        args += ["--inputs", write_json(w.path("in.json"), frames(*inputs))]
    code, err = run_headless(*args)
    assert code == expect, (code, err)
    return read_jsonl(w.path("o.jsonl")) if expect == 0 else None


def ev(rows, name):
    return [(r["tick"], r["data"]) for r in events(rows, name)]


DOCK_NOW = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}]


class Manifest(unittest.TestCase):
    def test_v11_standard_data(self):
        c = contract()
        self.assertIn(c["contract_version"], ("1.2", "1.3"))  # v1.1 → v1.2 (độ tươi) → v1.3 (phát hành)
        t = c["tuning"]
        self.assertEqual(len(t["menu"]), 6)
        self.assertEqual([s["id"] for s in t["quan"]["stoves"]], ["B1", "B2"])
        self.assertEqual(len(t["quan"]["tables"]), 4)
        self.assertEqual(t["gather"]["fish_initial"], 8)
        for p in t["day_plan"]:
            ing = {}
            for d, n in p["dishes"].items():
                for k, v in t["menu"][d]["recipe"].items():
                    ing[k] = ing.get(k, 0) + v * n
            self.assertEqual(p["ingredients"], ing)


class Fish(unittest.TestCase):
    def test_initial_schools_on_distinct_spawn_points(self):
        g = T()["gather"]
        with Workdir() as w:
            s = snapshots(run(w, "gather", ticks=0))[0]
            self.assertEqual(len(s["fish"]), g["fish_initial"])
            pts = [tuple(f["pos"]) for f in s["fish"]]
            self.assertEqual(len(set(pts)), len(pts))
            for f in s["fish"]:
                self.assertIn(f["pos"][0], g["fish_spawn_x"])
                self.assertIn(f["pos"][1], g["fish_spawn_depths"][f["kind"]])

    def test_swim_speed_and_depth_band(self):
        g = T()["gather"]
        with Workdir() as w:
            sc = {"gather": {"monsters": [], "fish": [{"id": "F1", "kind": "ca_loc", "pos": [50, 14], "heading_deg": 0}]}}
            rows = run(w, "gather", sc, ticks=60)
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertAlmostEqual(s[60]["fish"][0]["pos"][0] - 50, g["fish_speed"], delta=0.01)
            self.assertEqual(s[60]["fish"][0]["age_ticks"], 60)

    def test_reflect_at_x_edge(self):
        with Workdir() as w:
            sc = {"gather": {"monsters": [], "fish": [{"id": "F1", "kind": "ca_loc", "pos": [95.99, 14], "heading_deg": 0}]}}
            f = snapshots(run(w, "gather", sc, ticks=2))[-1]["fish"][0]
            self.assertLessEqual(f["pos"][0], 96)
            self.assertAlmostEqual(f["heading_deg"], 180, delta=0.01)

    def test_turn_on_120th_swim_step(self):
        with Workdir() as w:
            sc = {"gather": {"monsters": [], "fish": [{"id": "F1", "kind": "ca_loc", "pos": [50, 14], "heading_deg": 0, "age_ticks": 118}]}}
            s = {r["tick"]: r for r in snapshots(run(w, "gather", sc, ticks=2))}
            self.assertEqual(s[1]["fish"][0]["heading_deg"], 0)
            self.assertNotEqual(s[2]["fish"][0]["heading_deg"], 0)

    def test_spawn_schedule_and_cap(self):
        g = T()["gather"]
        with Workdir() as w:
            rows = run(w, "gather", {"gather": {"monsters": []}}, ticks=g["fish_spawn_ticks"] * 6, every=1000)
            sp = ev(rows, "fish_spawned")
            self.assertEqual([t for t, _ in sp], [g["fish_spawn_ticks"] * k for k in range(1, 1 + g["fish_max"] - g["fish_initial"])])
            self.assertEqual(sp[0][1]["id"], f"F{g['fish_initial'] + 1}")
            self.assertEqual(len(snapshots(rows)[-1]["fish"]), g["fish_max"])

    def test_random_fish_false_static(self):
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "monsters": [], "fish": [{"id": "F1", "kind": "ca_keo", "pos": [50, 25]}]}}
            rows = run(w, "gather", sc, ticks=400, every=400)
            self.assertEqual(snapshots(rows)[-1]["fish"][0]["pos"], [50, 25])
            self.assertEqual(ev(rows, "fish_spawned"), [])

    def test_catch_ca_keo_yield(self):
        g = T()["gather"]
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "monsters": [], "player": {"pos": [50, 25]},
                             "fish": [{"id": "F1", "kind": "ca_keo", "pos": [51, 25]}]}}
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "catch": True}], ticks=1)
            self.assertEqual(ev(rows, "fish_caught"), [(1, {"fish_id": "F1", "kind": "ca_keo", "yield": g["fish_yield"]["ca_keo"]})])


def croc(pos, **kw):
    m = {"id": "M1", "kind": "ca_sau", "pos": pos, "waypoints": [[60, 24], [64, 24]]}
    m.update(kw)
    return m


class Monster(unittest.TestCase):
    def test_default_layout_day1(self):
        with Workdir() as w:
            s = snapshots(run(w, "gather", ticks=0))[0]
            self.assertEqual([m["id"] for m in s["monsters"]], ["M1"])
            self.assertEqual(s["monsters"][0]["pos"], [60, 24])
            self.assertEqual(s["monsters"][0]["target_idx"], 1)

    def test_patrol_speed_and_turnaround(self):
        sp = T()["gather"]["monsters"]["species"]["ca_sau"]
        with Workdir() as w:
            rows = run(w, "gather", {"gather": {"random_fish": False}}, ticks=250, every=60)
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertAlmostEqual(s[60]["monsters"][0]["pos"][0], 60 + sp["patrol_speed"], delta=0.01)
            self.assertEqual(s[240]["monsters"][0]["target_idx"], 0)  # tới [64,24] ở tick 240, đổi mục tiêu

    def test_chase_when_player_deep_and_near(self):
        sp = T()["gather"]["monsters"]["species"]["ca_sau"]
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "player": {"pos": [50, 24]}, "monsters": [croc([58, 24])]}}
            rows = run(w, "gather", sc, ticks=1)
            m = snapshots(rows)[-1]["monsters"][0]
            self.assertEqual(m["state"], "chase")
            self.assertAlmostEqual(m["pos"][0], 58 - sp["chase_speed"] / 60, places=3)
        with Workdir() as w:  # người chơi ở d < 10: không đuổi
            sc = {"gather": {"random_fish": False, "player": {"pos": [55, 5]}, "monsters": [croc([58, 12])]}}
            self.assertEqual(snapshots(run(w, "gather", sc, ticks=1))[-1]["monsters"][0]["state"], "patrol")

    def test_hit_drops_half_lifo_invuln_and_recoil(self):
        mt = T()["gather"]["monsters"]
        sp = mt["species"]["ca_sau"]
        with Workdir() as w:
            hold = items("ca_loc", "bong_sung", "ca_linh", "ca_keo", "keo_neo")
            sc = {"gather": {"random_fish": False, "hold": hold, "player": {"pos": [62, 24]}, "monsters": [croc([62.5, 24])]}}
            rows = run(w, "gather", sc, ticks=sp["recoil_ticks"] + 2)
            hits = ev(rows, "monster_hit")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0][0], 1)
            self.assertEqual(ids_of(hits[0][1]["lost"]), ["I5", "I4"])  # floor(5 × 0.5) = 2, LIFO
            self.assertEqual(kinds_of(hits[0][1]["lost"]), ["keo_neo", "ca_keo"])
            self.assertEqual(hits[0][1]["hp"], T()["gather"]["hp_max"] - 1)
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertEqual(s[1]["player"]["invuln_ticks"], mt["invuln_ticks"])
            self.assertEqual(s[1]["monsters"][0]["state"], "recoil")
            self.assertEqual(s[1]["monsters"][0]["recoil_dir"], [1, 0])
            moved = s[1 + sp["recoil_ticks"]]["monsters"][0]["pos"][0] - s[1]["monsters"][0]["pos"][0]
            self.assertAlmostEqual(moved, sp["recoil_dist"], delta=0.01)
            self.assertEqual(s[1 + sp["recoil_ticks"]]["monsters"][0]["state"], "patrol")

    def test_no_hit_while_invuln_and_shallow(self):
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "player": {"pos": [62, 24], "invuln_ticks": 50}, "monsters": [croc([62.5, 24])]}}
            self.assertEqual(ev(run(w, "gather", sc, ticks=20), "monster_hit"), [])

    def test_faint_by_monster_keeps_order(self):
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "hold": items("ca_loc", "bong_sung", "ca_linh"), "player": {"pos": [62, 24], "hp": 1},
                             "monsters": [croc([62.5, 24])]}}
            rows = run(w, "gather", sc, ticks=5)
            names = [r["name"] for r in events(rows)]
            self.assertEqual(names, ["monster_hit", "faint", "gather_end"])
            fa = ev(rows, "faint")[0][1]
            self.assertEqual((fa["cause"], ids_of(fa["lost"]), fa["hp"]), ("monster", ["I2", "I1"], 0))
            self.assertEqual(ev(rows, "gather_end")[0][1]["inventory"], {"items": []})

    def test_choke_ignores_invuln_and_keeps_hold(self):
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "monsters": [], "hold": items("ca_loc"),
                             "player": {"pos": [30, 15], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "invuln_ticks": 80}}}
            rows = run(w, "gather", sc, ticks=1)
            self.assertEqual(len(ev(rows, "choke")), 1)
            self.assertEqual(ids_of(snapshots(rows)[-1]["hold"]), ["I1"])


def day_inputs(*extra):
    return [*DOCK_NOW, *extra]


class Day(unittest.TestCase):
    def test_day_start_order_and_plan_d1(self):
        with Workdir() as w:
            rows = run(w, "day", ticks=0, extra=("--days", "1"))
            first = [(r["type"], r.get("name")) for r in rows[:4]]
            self.assertEqual(first, [("event", "day_start"), ("event", "day_plan"), ("event", "phase_start"), ("snapshot", None)])
            self.assertEqual(rows[1]["day"], 1)
            self.assertEqual(rows[1]["data"], {"dishes": T()["day_plan"][0]["dishes"], "ingredients": T()["day_plan"][0]["ingredients"]})
            s = rows[3]
            for k in ("day", "day_plan", "upgrades", "active_upgrades"):
                self.assertIn(k, s)

    def test_phase_changes_same_tick_and_snapshot(self):
        q = T()["quan"]
        dur = int(q["duration_s"] * 60)
        with Workdir() as w:
            sc = {"gather": {"hold": items("ca_loc"), "random_fish": False}}
            rows = run(w, "day", sc, inputs=day_inputs(), ticks=dur + 2, every=5000, extra=("--days", "1"))
            ge = events(rows, "gather_end")[0]
            ps = [r for r in events(rows, "phase_start")]
            self.assertEqual(ge["phase"], "gather")
            self.assertEqual((ps[1]["tick"], ps[1]["phase"]), (1, "quan"))
            snap1 = [r for r in snapshots(rows) if r["tick"] == 1][0]
            self.assertEqual((snap1["phase"], snap1["phase_tick"]), ("quan", 0))
            # bàn giao cùng tick, không hao thêm: fresh = 100 − 1 bước gather (2/240)
            self.assertEqual(ids_of(snap1["stock"]), ["I1"])
            self.assertAlmostEqual(snap1["stock"][0]["fresh"], 100 - 2 / 240, delta=0.01)
            self.assertEqual((ps[2]["tick"], ps[2]["phase"]), (1 + dur, "shop"))
            self.assertEqual(events(rows, "quan_end")[0]["phase"], "quan")

    def test_five_days_plan_and_upgrades_next_day(self):
        t = T()
        dur = int(t["quan"]["duration_s"] * 60)
        day_len = 1 + dur + 1  # cập bến tick 0, quán đủ ca, đóng Shop bước đầu
        shop_frames = []
        for d in range(5):
            start = d * day_len
            if d:
                shop_frames += [{"tick": start, "interact": True}, {"tick": start + 1, "interact": False}]
            k = start + 1 + dur  # bước đầu tiên của Shop
            if d == 0:
                shop_frames.append({"tick": k, "buy": "oxygen", "shop_done": True})
            else:
                shop_frames.append({"tick": k, "shop_done": True})
            shop_frames.append({"tick": k + 1, "shop_done": False})
        shop_frames[0:0] = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}]
        merged = {}
        for f in shop_frames:
            merged.setdefault(f["tick"], {}).update(f)
        shop_frames = [merged[k] for k in sorted(merged)]
        with Workdir() as w:
            sc = {"day": {"money": 300, "earned": 300}, "gather": {"random_fish": False}}
            rows = run(w, "day", sc, inputs=shop_frames, ticks=5 * day_len + 5, every=100000, extra=("--days", "5"))
            plans = [r["data"] for r in events(rows, "day_plan")]
            self.assertEqual(plans, [{"dishes": p["dishes"], "ingredients": p["ingredients"]} for p in t["day_plan"]])
            bought = ev(rows, "bought")
            self.assertEqual(bought[0][1], {"upgrade": "oxygen", "level": 1, "price": 200, "money": 100})
            gathers = [r for r in snapshots(rows) if r["phase"] == "gather" and r["phase_tick"] == 0]
            self.assertEqual(gathers[0]["player"]["oxygen_max_ticks"], int(t["gather"]["oxygen_max_s"] * 60))
            self.assertEqual(gathers[1]["player"]["oxygen_max_ticks"], int(t["shop"]["upgrades"]["oxygen"][0]["oxygen_max_s"] * 60))
            self.assertEqual(gathers[1]["active_upgrades"], {"oxygen": 1})
            self.assertEqual(gathers[2]["monsters"][-1]["id"], "M2")  # M2 từ Ngày 3
            self.assertEqual(len(gathers[1]["monsters"]), 1)
            end = rows[-1]
            self.assertEqual((end["reason"], end["days_completed"], end["state"]), ("days_complete", 5, "finished"))
            ends = events(rows, "shop_end")
            self.assertEqual([e["day"] for e in ends], [1, 2, 3, 4, 5])

    def test_shop_buy_failed_and_auto_close(self):
        t = T()
        dur = int(t["quan"]["duration_s"] * 60)
        k = 1 + dur
        with Workdir() as w:
            sc = {"day": {"money": 150, "earned": 250, "upgrades": {"hp": 2}}, "gather": {"random_fish": False}}
            inputs = [*DOCK_NOW, {"tick": k, "buy": "hp"}, {"tick": k + 1, "buy": "oxygen"}, {"tick": k + 2, "buy": "lao"}]
            rows = run(w, "day", sc, inputs=inputs, ticks=k + t["shop"]["max_ticks"] + 5, every=100000, extra=("--days", "1"))
            fails = [d for _, d in ev(rows, "buy_failed")]
            self.assertEqual(fails, [{"action": "hp", "reason": "max_level"}, {"action": "oxygen", "reason": "funds"},
                                     {"action": "lao", "reason": "unknown"}])
            self.assertEqual(ev(rows, "shop_end"), [(k + t["shop"]["max_ticks"], {"reason": "time"})])
            self.assertEqual(rows[-1]["money"], 150)

    def test_day_menu_filtered_by_plan(self):
        with Workdir() as w:
            sc = {"gather": {"random_fish": False, "hold": items("ca_loc", "ca_loc", "ca_keo", "ca_keo", "bong_sung", "bong_sung")}}
            rows = run(w, "day", sc, inputs=DOCK_NOW, ticks=10800, every=100000, extra=("--days", "1"))
            dishes = {d["dish_id"] for _, d in ev(rows, "customer_arrived")}
            self.assertTrue(dishes)
            self.assertTrue(dishes <= set(T()["day_plan"][0]["dishes"]), dishes)

    def test_bad_day_inputs_exit_2(self):
        with Workdir() as w:
            for sc in ({"quan": {"stock": items("ca_loc")}}, {"quan": {"reputation": 2}}, {"day": {"money": 10, "earned": 5}},
                       {"day": {"money": 10}}, {"day": {"upgrades": {"oxygen": 3}}},
                       {"day": {"day_plan": [{"day": 1, "dishes": {"ca_loc_nuong_trui": 1}, "ingredients": {"ca_loc": 2}}]}},
                       {"shop": {}}):
                self.assertIsNone(run(w, "day", sc, ticks=0, expect=2), sc)
            self.assertIsNone(run(w, "day", ticks=0, extra=("--days", "6"), expect=2))
            self.assertIsNone(run(w, "gather", ticks=0, extra=("--days", "1"), expect=2))
            self.assertIsNone(run(w, "day", inputs=[{"tick": 0, "buy": ""}], ticks=0, expect=2))
            self.assertIsNone(run(w, "day", inputs=[{"tick": 0, "attack": True}], ticks=0, expect=2))

    def test_day_one_runs_under_20s(self):
        with Workdir() as w:
            t0 = time.time()
            rows = run(w, "day", ticks=22200, every=10, extra=("--days", "1"))
            self.assertLess(time.time() - t0, 20)
            self.assertEqual(rows[-1]["reason"], "days_complete")
            self.assertEqual(rows[-1]["ticks"], 22200)


class Pause(unittest.TestCase):
    def test_pause_freezes_sim_and_resume_runs_same_step(self):
        with Workdir() as w:
            inputs = [{"tick": 2, "pause": True}, {"tick": 3, "pause": False, "interact": True},
                      {"tick": 4, "interact": False}, {"tick": 6, "pause": True}]
            sc = {"gather": {"random_fish": False, "hold": items("ca_loc")}}
            rows = run(w, "gather", sc, inputs=inputs, ticks=10)
            self.assertEqual(ev(rows, "paused"), [(3, {})])
            self.assertEqual(ev(rows, "resumed"), [(7, {})])
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertEqual(s[5]["state"], "paused")
            self.assertEqual(s[5]["sim_tick"], 2)
            self.assertEqual(s[5]["time_left_ticks"], s[3]["time_left_ticks"])
            # interact bấm trong lúc pause không tạo cạnh; đang trong bến mà không docked
            self.assertEqual(ev(rows, "gather_end"), [])
            self.assertEqual(s[7]["sim_tick"], 3)
            self.assertEqual(rows[-1]["sim_tick"], 6)

    def test_pause_in_quan_freezes_customers(self):
        q = T()["quan"]
        with Workdir() as w:
            rows = run(w, "quan", {"quan": {"stock": items("ca_loc")}}, inputs=[{"tick": 0, "pause": True}],
                       ticks=q["first_customer_tick"] + 5, every=1000)
            self.assertEqual(ev(rows, "customer_arrived"), [])
            self.assertEqual(rows[-1]["state"], "paused")


class QuanV11(unittest.TestCase):
    def test_standalone_uses_all_dishes_and_four_tables(self):
        q = T()["quan"]
        stock = items(*[k for k in ("ca_loc", "ca_linh", "ca_keo", "keo_neo", "bong_sung", "bong_dien_dien") for _ in range(9)])
        with Workdir() as w:
            rows = run(w, "quan", {"quan": {"stock": stock}}, ticks=q["first_customer_tick"] + 900 * 3 + 1, every=10000, seed=5)
            arr = ev(rows, "customer_arrived")
            self.assertEqual([d["table_id"] for _, d in arr], ["T1", "T2", "T3", "T4"])
            self.assertEqual([t for t, _ in arr], [120 + 900 * k for k in range(4)])

    def test_second_stove_picks_next_oldest_order(self):
        with Workdir() as w:
            sc = {"quan": {"random_customers": False, "stock": items("ca_loc", "ca_loc"), "player": {"pos": [5, 7]},
                           "customers": [{"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 5},
                                         {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 5}]}}
            rows = run(w, "quan", sc, inputs=[{"tick": 0, "interact": True}], ticks=1)
            self.assertEqual(ev(rows, "cook_started")[0][1]["stove_id"], "B2")
            self.assertEqual(ev(rows, "cook_started")[0][1]["order_id"], "C2")  # hòa order_tick -> id bàn T1


class Determinism(unittest.TestCase):
    def test_day_bytes_identical(self):
        with Workdir() as w:
            inp = write_json(w.path("in.json"), frames({"tick": 0, "move": [1, 1]}, {"tick": 400, "move": [0, -1]}))
            for i in (1, 2):
                code, err = run_headless("--mode", "day", "--seed", "9", "--ticks", "3000", "--inputs", inp,
                                         "--out", w.path(f"o{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("o1.jsonl"), "rb") as a, open(w.path("o2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()

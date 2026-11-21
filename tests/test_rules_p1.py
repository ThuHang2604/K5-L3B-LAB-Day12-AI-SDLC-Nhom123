"""Test luật của nhóm (hộp đen qua headless_cmd), bám các AC Phase 1 và Test Contract mục F.

Số đọc từ game.contract.json nên dùng được cả với số chuẩn Phase 2.
"""

import json
import math
import unittest

from helpers import Workdir, events, frames, ids_of, items, kinds_of, read_jsonl, run_headless, snapshots, write_json


def tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]


def run(w, mode, scenario=None, inputs=None, ticks=10, every=1, seed=1, extra=()):
    args = ["--mode", mode, "--seed", str(seed), "--ticks", str(ticks), "--out", w.path("o.jsonl"),
            "--snapshot-every", str(every), *extra]
    if scenario is not None:
        args += ["--scenario", write_json(w.path("sc.json"), {mode: scenario})]
    if inputs is not None:
        args += ["--inputs", write_json(w.path("in.json"), frames(*inputs))]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def ev(rows, name):
    return [(r["tick"], r["data"]) for r in events(rows, name)]


NOFISH = {"random_fish": False, "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [44, 0]}]}


class Oxygen(unittest.TestCase):
    def test_ac_oxy_empty_and_first_choke_at_t_plus_59(self):
        with Workdir() as w:
            sc = dict(NOFISH, player={"pos": [50, 10], "oxygen_ticks": 3})
            rows = run(w, "gather", sc, ticks=70)
            self.assertEqual(ev(rows, "oxygen_empty"), [(3, {"oxygen_ticks": 0})])
            self.assertEqual(ev(rows, "choke"), [(3 + 59, {"hp": tuning()["gather"]["hp_max"] - 1})])

    def test_ac_faint_drops_hold_lifo_and_empty_inventory(self):
        with Workdir() as w:
            sc = dict(NOFISH, monsters=[], hold=items("ca_loc", "bong_sung", "ca_linh"),
                      player={"pos": [50, 10], "oxygen_ticks": 0, "hp": 1, "zero_oxy_ticks": 58})
            inv = w.path("inv.json")
            rows = run(w, "gather", sc, ticks=10, extra=("--inventory-out", inv))
            self.assertEqual(ev(rows, "choke"), [(2, {"hp": 0})])
            faint = ev(rows, "faint")
            self.assertEqual(faint[0][0], 2)
            self.assertEqual(ids_of(faint[0][1]["lost"]), ["I3", "I2", "I1"])  # LIFO theo thứ tự vào giỏ
            self.assertEqual(kinds_of(faint[0][1]["lost"]), ["ca_linh", "bong_sung", "ca_loc"])
            end = ev(rows, "gather_end")[0][1]
            self.assertEqual(end, {"reason": "fainted", "inventory": {"items": []}})
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

    def test_surface_refill_resets_choke(self):
        with Workdir() as w:
            sc = dict(NOFISH, player={"pos": [50, 0.6], "oxygen_ticks": 0, "zero_oxy_ticks": 30})
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "move": [0, -1]}], ticks=5)
            s = snapshots(rows)[-1]["player"]
            self.assertTrue(s["at_surface"])
            self.assertEqual(s["zero_oxy_ticks"], 0)
            self.assertGreater(s["oxygen_ticks"], 0)
            self.assertEqual(len(ev(rows, "surface")), 1)


class Harvest(unittest.TestCase):
    def test_ac_harvest_on_radius_edge_and_regrow(self):
        g = tuning()["gather"]
        with Workdir() as w:
            sc = {"random_fish": False, "player": {"pos": [20, 0]},
                  "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [20 + g["interact_radius"], 0]}]}
            regrow = int(g["regrow_s"] * 60)
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "interact": True}], ticks=regrow + 3, every=600)
            self.assertEqual(ev(rows, "gather"), [(1, {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1})])
            self.assertEqual(ev(rows, "node_regrown"), [(1 + regrow, {"node_id": "N1"})])

    def test_hold_full_keeps_node(self):
        g = tuning()["gather"]
        with Workdir() as w:
            sc = {"random_fish": False, "player": {"pos": [20, 0]}, "hold": items(*["ca_loc"] * g["hold_capacity"]),
                  "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [21, 0]}]}
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "interact": True}], ticks=2)
            self.assertEqual(ev(rows, "hold_full"), [(1, {"action": "gather", "node_id": "N1", "required": 1, "free": 0})])
            self.assertTrue(snapshots(rows)[-1]["nodes"][0]["ready"])

    def test_no_harvest_underwater(self):
        with Workdir() as w:
            sc = {"random_fish": False, "player": {"pos": [20, 1.5]}, "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [20, 0]}]}
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "interact": True}], ticks=2)
            self.assertEqual(ev(rows, "gather"), [])

    def test_nearest_node_tie_by_id(self):
        with Workdir() as w:
            sc = {"random_fish": False, "player": {"pos": [20, 0]},
                  "nodes": [{"id": "N10", "kind": "bong_sung", "pos": [21, 0]}, {"id": "N2", "kind": "bong_sung", "pos": [19, 0]}]}
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "interact": True}], ticks=1)
            self.assertEqual(ev(rows, "gather")[0][1]["node_id"], "N2")


class Catch(unittest.TestCase):
    def test_ac_catch_yield_and_cooldown(self):
        g = tuning()["gather"]
        cd = int(g["catch_cooldown_s"] * 60)
        with Workdir() as w:
            sc = {"random_fish": False, "player": {"pos": [30, 10]},
                  "fish": [{"id": "F1", "kind": "ca_linh", "pos": [31, 10]}, {"id": "F2", "kind": "ca_loc", "pos": [29.5, 10]}]}
            # bắt ở bước 0 (tick 1), thử lại ở bước 1 (còn hồi), bước cd (tick cd+1) được
            inputs = [{"tick": 0, "catch": True}, {"tick": 1, "catch": False}, {"tick": 2, "catch": True},
                      {"tick": 3, "catch": False}, {"tick": cd, "catch": True}]
            rows = run(w, "gather", sc, inputs=inputs, ticks=cd + 2)
            caught = ev(rows, "fish_caught")
            self.assertEqual(caught[0], (1, {"fish_id": "F2", "kind": "ca_loc", "yield": g["fish_yield"]["ca_loc"]}))
            self.assertEqual(caught[1], (cd + 1, {"fish_id": "F1", "kind": "ca_linh", "yield": g["fish_yield"]["ca_linh"]}))
            self.assertEqual(len(caught), 2)

    def test_catch_hold_full_no_cooldown(self):
        g = tuning()["gather"]
        with Workdir() as w:
            sc = {"random_fish": False, "monsters": [], "player": {"pos": [30, 10]}, "hold": items(*["ca_loc"] * (g["hold_capacity"] - 1)),
                  "fish": [{"id": "F1", "kind": "ca_linh", "pos": [31, 10]}]}
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "catch": True}], ticks=1)
            self.assertEqual(ev(rows, "hold_full"), [(1, {"action": "catch", "fish_id": "F1", "required": 3, "free": 1})])
            self.assertEqual(snapshots(rows)[-1]["player"]["catch_cd_ticks"], 0)


def quan_sc(**kw):
    base = {"random_customers": False}
    base.update(kw)
    return base


class Quan(unittest.TestCase):
    def test_ac_full_order_cook_pick_serve_pay_tip(self):
        t = tuning()
        q, menu = t["quan"], t["menu"]
        dish = menu["ca_loc_nuong_trui"]
        cook = int(dish["cook_s"] * 60)
        eat = int(q["eat_s"] * 60)
        with Workdir() as w:
            sc = quan_sc(stock=items("ca_loc"), player={"pos": [2, 7]},
                         customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}])
            # E tại bếp (tick 0), chờ chín, E nhặt, đi tới bàn T1 [9,2] (đặt thẳng bằng scenario khó) -> dùng move
            inputs = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                      {"tick": cook + 1, "interact": True}, {"tick": cook + 2, "interact": False}]
            rows = run(w, "quan", sc, inputs=inputs, ticks=cook + 3)
            cs = ev(rows, "cook_started")
            self.assertEqual(cs[0][0], 1)
            # v1.2: kho hao 1 đơn vị (1/240 điểm) ở bước 0 trước khi nấu -> giá = floor(60 × 99.9958/100) = 59
            price = math.floor(dish["price"] * (24000 - 1) / 24000)
            self.assertEqual({k: cs[0][1][k] for k in ("stove_id", "order_id", "dish_id", "base_price")},
                             {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": price})
            self.assertEqual(ids_of(cs[0][1]["items"]), ["I1"])
            self.assertEqual(ev(rows, "dish_ready")[0][0], 1 + cook)
            self.assertEqual(ev(rows, "dish_picked")[0][0], cook + 2)
            last = snapshots(rows)[-1]
            self.assertEqual(last["hand"], {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": price})
            self.assertEqual(last["stock"], [])
        # phục vụ: dựng tay đang cầm món, đứng cạnh bàn
        with Workdir() as w:
            hand = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": dish["price"]}
            sc = quan_sc(stock=[], hand=hand, player={"pos": [9, 3]},
                         customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}])
            rows = run(w, "quan", sc, inputs=[{"tick": 0, "interact": True}], ticks=eat + 2)
            tip = math.floor(dish["price"] * q["tip_rate"])
            served = ev(rows, "served")
            self.assertEqual(served[0][0], 1)
            self.assertEqual(served[0][1]["tip"], tip)
            paid = ev(rows, "paid")
            self.assertEqual(paid, [(1 + eat, {"order_id": "C1", "table_id": "T1", "base_price": dish["price"], "tip": tip,
                                               "amount": dish["price"] + tip, "reason": "finished_eating"})])
            end = snapshots(rows)[-1]
            self.assertEqual(end["money"], dish["price"] + tip)
            self.assertAlmostEqual(end["reputation"], q["reputation_initial"] + q["tip_reputation"], places=6)
            self.assertEqual(end["score"], end["earned"] + 100 * math.floor(end["reputation"]))

    def test_no_tip_below_half_patience(self):
        t = tuning()
        q = t["quan"]
        full = int(q["patience_s"] * 60)
        with Workdir() as w:
            hand = {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": t["menu"]["goi_bong_sung"]["price"]}
            sc = quan_sc(hand=hand, player={"pos": [9, 3]}, customers=[
                {"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "order_status": "assigned",
                 "patience_ticks_left": full // 2}])
            rows = run(w, "quan", sc, inputs=[{"tick": 0, "interact": True}], ticks=1)
            self.assertEqual(ev(rows, "served")[0][1]["tip"], 0)  # còn full/2 - 1 sau bước 1 < 50%

    def test_ac_patience_left_reputation(self):
        q = tuning()["quan"]
        with Workdir() as w:
            sc = quan_sc(stock=items("ca_loc"), customers=[
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "patience_ticks_left": 3}])
            rows = run(w, "quan", sc, ticks=5)
            left = ev(rows, "customer_left")
            self.assertEqual(left, [(3, {"order_id": "C1", "table_id": "T1", "reason": "patience",
                                         "reputation": q["reputation_initial"] + q["left_reputation_delta"]})])
            self.assertEqual(ids_of(snapshots(rows)[-1]["stock"]), ["I1"], "nhả phần giữ, tồn vật lý giữ nguyên")

    def test_closing_pays_eating_and_releases_waiting(self):
        q = tuning()["quan"]
        with Workdir() as w:
            sc = quan_sc(time_left_ticks=2, stock=items("ca_loc"), customers=[
                {"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "state": "eating", "order_status": "served",
                 "eat_ticks_left": 100, "base_price": 40, "tip": 8},
                {"id": "C2", "table_id": "T2" if len(q["tables"]) > 1 else "T1", "dish_id": "ca_loc_nuong_trui"}][:2 if len(q["tables"]) > 1 else 1])
            rows = run(w, "quan", sc, ticks=10)
            self.assertEqual(ev(rows, "paid")[0], (2, {"order_id": "C1", "table_id": "T1", "base_price": 40, "tip": 8,
                                                      "amount": 48, "reason": "closing"}))
            if len(q["tables"]) > 1:
                self.assertEqual(ev(rows, "customer_left")[0][1]["reason"], "closing")
            qe = ev(rows, "quan_end")[0]
            self.assertEqual(qe[0], 2)
            self.assertEqual(qe[1]["money"], 48)
            self.assertEqual(rows[-1]["reason"], "time")

    def test_ac_customer_schedule_reserve_and_no_dish(self):
        q = tuning()["quan"]
        first = q["first_customer_tick"]
        with Workdir() as w:
            rows = run(w, "quan", {"stock": items("ca_loc")}, ticks=first + 1, every=first)
            arr = ev(rows, "customer_arrived")
            self.assertEqual(arr, [(first, {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})])
            c = snapshots(rows)[-1]["customers"][0]
            self.assertEqual(c["reserved"], ["I1"])
            self.assertEqual(c["order_tick"], first)
        with Workdir() as w:
            rows = run(w, "quan", {}, ticks=first + 1, every=first)
            self.assertEqual(ev(rows, "no_dish"), [(first, {})])

    def test_scenario_conflicts_exit_2(self):
        bad = [
            {"stock": [], "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
            {"stock": items("ca_loc"), "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                                       "reserved": ["I1", "I9"]}]},
            {"stock": items("ca_loc", fresh=29.5), "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                                                  "reserved": ["I1"]}]},
            {"stock": items("ca_loc", "ca_loc"), "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}]},
            {"stock": {"ca_loc": 1}},
            {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 101}]},
            {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 50}, {"id": "I1", "kind": "ca_loc", "fresh": 60}]},
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "pho_bo"}]},
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "state": "eating", "order_status": "served",
                            "eat_ticks_left": 10}]},
            {"stoves": [{"id": "B9", "state": "idle"}]},
            {"stoves": [{"id": "B1", "state": "cooking", "cook_ticks_left": 0,
                         "dish": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40}}],
             "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "order_status": "assigned"}]},
            {"hand": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40},
             "stoves": [{"id": "B1", "state": "ready", "dish": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40}}],
             "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "order_status": "assigned"}]},
            {"stock": [{"id": "I1", "kind": "ca_la_lung", "fresh": 50}]},
        ]
        with Workdir() as w:
            for block in bad:
                sc = write_json(w.path("sc.json"), {"quan": block})
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", w.path("o.jsonl"))
                self.assertEqual(code, 2, block)


if __name__ == "__main__":
    unittest.main()

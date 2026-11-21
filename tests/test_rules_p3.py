"""Test luật Phase 3 — "Mùa Nước Nổi": kho cá thể + độ tươi (Test Contract v1.2), hộp đen qua headless_cmd."""

import json
import math
import unittest

from helpers import Workdir, events, frames, ids_of, items, read_jsonl, run_headless, snapshots, write_json

U = 240  # đơn vị mỗi điểm tươi


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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


QUIET = {"random_fish": False, "monsters": []}


class Threshold(unittest.TestCase):
    def test_ac_p3_spoiled_exactly_at_30_in_hold(self):
        with Workdir() as w:
            rows = run(w, "gather", {"gather": dict(QUIET, hold=items("ca_linh", fresh=30))}, ticks=1)
            self.assertEqual(events(rows, "spoiled"), [
                {"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
                 "data": {"item_id": "I1", "kind": "ca_linh", "location": "hold"}}])

    def test_spoiled_once_and_by_id(self):
        with Workdir() as w:
            hold = [{"id": "I2", "kind": "ca_loc", "fresh": 30}, {"id": "I1", "kind": "ca_linh", "fresh": 30},
                    {"id": "I3", "kind": "ca_keo", "fresh": 31}]
            rows = run(w, "gather", {"gather": dict(QUIET, hold=hold)}, ticks=200, every=100)
            sp = ev(rows, "spoiled")
            self.assertEqual([(t, d["item_id"]) for t, d in sp], [(1, "I1"), (1, "I2"), (121, "I3")])

    def test_gather_decay_half_per_second_clamped(self):
        with Workdir() as w:
            rows = run(w, "gather", {"gather": dict(QUIET, hold=items("ca_loc", fresh=0.5))}, ticks=120, every=60)
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertAlmostEqual(s[60]["hold"][0]["fresh"], 0.0, delta=0.01)
            self.assertEqual(s[120]["hold"][0]["fresh"], 0)

    def test_new_item_fresh_100_ids_continue(self):
        with Workdir() as w:
            sc = {"gather": dict(QUIET, player={"pos": [12, 0]}, hold=[{"id": "I7", "kind": "ca_loc", "fresh": 80}])}
            rows = run(w, "gather", sc, inputs=[{"tick": 0, "interact": True}], ticks=2)
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertEqual(ids_of(s[1]["hold"]), ["I7", "I8"])
            self.assertEqual(s[1]["hold"][1]["fresh"], 100)  # hàng mới, hao từ bước sau
            self.assertAlmostEqual(s[2]["hold"][1]["fresh"], 100 - 2 / U, delta=0.001)


class Handoff(unittest.TestCase):
    def test_ac_p3_file_handoff_exact(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": dict(QUIET, hold=items("ca_linh"))})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "42", "--scenario", sc, "--inputs", inp, "--ticks", "1",
                                     "--out", w.path("g.jsonl"), "--inventory-out", inv)
            self.assertEqual(code, 0, err)
            saved = load(inv)
            self.assertEqual(saved, {"items": [{"id": "I1", "kind": "ca_linh", "fresh": (24000 - 2) / U}]})
            code, err = run_headless("--mode", "quan", "--seed", "42", "--inventory", inv, "--ticks", "0",
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            st = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
            self.assertEqual([(x["id"], x["kind"]) for x in st], [("I1", "ca_linh")])
            self.assertAlmostEqual(st[0]["fresh"], saved["items"][0]["fresh"], delta=0.01)

    def test_file_keeps_branch_at_threshold(self):
        """Kho ghi đủ chính xác: hàng 30.0083 (30 + 2/240) không thành ươn sau khi đọc lại."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": dict(QUIET, hold=items("ca_loc", fresh=30 + 4 / U))})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("k.json")
            run_headless("--mode", "gather", "--seed", "1", "--scenario", sc, "--inputs", inp, "--ticks", "1",
                         "--out", w.path("g.jsonl"), "--inventory-out", inv)
            code, _ = run_headless("--mode", "quan", "--seed", "1", "--inventory", inv, "--ticks", "3",
                                   "--snapshot-every", "1", "--out", w.path("q.jsonl"))
            rows = read_jsonl(w.path("q.jsonl"))
            self.assertEqual(ev(rows, "spoiled"), [(3, {"item_id": "I1", "kind": "ca_loc", "location": "stock"})])

    def test_count_schema_and_bad_instances_exit_2(self):
        with Workdir() as w:
            bad = [{"items": {"ca_loc": 1}}, {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}] * 2},
                   {"items": [{"id": "", "kind": "ca_loc", "fresh": 100}]}, {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100.5}]},
                   {"items": [{"id": "I1", "kind": "ca_loc"}]}, {"items": [{"id": "I1", "kind": "ca_vang", "fresh": 1}]}]
            for b in bad:
                p = write_json(w.path("inv.json"), b)
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--inventory", p, "--ticks", "0", "--out", w.path("q.jsonl"))
                self.assertEqual(code, 2, b)

    def test_spoiled_goods_still_handed_over(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": dict(QUIET, hold=items("ca_loc", fresh=5))})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("k.json")
            run_headless("--mode", "gather", "--seed", "1", "--scenario", sc, "--inputs", inp, "--ticks", "1",
                         "--out", w.path("g.jsonl"), "--inventory-out", inv)
            self.assertEqual(ids_of(load(inv)["items"]), ["I1"])


def quan(stock, **kw):
    q = {"random_customers": False, "stock": stock}
    q.update(kw)
    return {"quan": q}


class QuanFresh(unittest.TestCase):
    def test_stock_decay_quarter_per_second_and_pause(self):
        with Workdir() as w:
            rows = run(w, "quan", quan(items("ca_loc", fresh=50)), inputs=[{"tick": 60, "pause": True}], ticks=120, every=60)
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertAlmostEqual(s[60]["stock"][0]["fresh"], 50 - 0.25, delta=0.001)
            self.assertAlmostEqual(s[120]["stock"][0]["fresh"], 50 - 0.25, delta=0.001)  # pause dừng hao

    def test_reserve_freshest_then_id_and_snapshot_ids(self):
        with Workdir() as w:
            stock = [{"id": "I1", "kind": "ca_loc", "fresh": 60}, {"id": "I2", "kind": "ca_loc", "fresh": 90},
                     {"id": "I3", "kind": "ca_loc", "fresh": 90}]
            rows = run(w, "quan", {"quan": {"stock": stock}}, ticks=120, every=120)
            self.assertEqual(snapshots(rows)[-1]["customers"][0]["reserved"], ["I2"])

    def test_ac_p3_reserved_item_spoils_rereserve_once(self):
        with Workdir() as w:
            stock = [{"id": "I1", "kind": "ca_loc", "fresh": 30}, {"id": "I2", "kind": "ca_loc", "fresh": 29.9},
                     {"id": "I3", "kind": "ca_loc", "fresh": 80}]
            # C1 giữ I1 (sắp ươn); I3 đang bị C2 giữ; sau khi I1 ươn: C1 không còn cá thể chưa ươn -> unfulfillable
            sc = quan(stock, customers=[
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"], "order_tick": 0},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "reserved": ["I3"], "order_tick": 1}])
            rows = run(w, "quan", sc, ticks=1)
            self.assertEqual(ev(rows, "spoiled"), [(1, {"item_id": "I1", "kind": "ca_loc", "location": "stock"})])
            c = {x["id"]: x for x in snapshots(rows)[-1]["customers"]}
            self.assertEqual((c["C1"]["order_status"], c["C1"]["reserved"]), ("unfulfillable", []))
            self.assertEqual(c["C2"]["reserved"], ["I3"])
        with Workdir() as w:
            stock = [{"id": "I1", "kind": "ca_loc", "fresh": 30}, {"id": "I4", "kind": "ca_loc", "fresh": 70}]
            sc = quan(stock, customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}])
            c = snapshots(run(w, "quan", sc, ticks=1))[-1]["customers"][0]
            self.assertEqual((c["order_status"], c["reserved"]), ("reserved", ["I4"]))

    def test_ac_p3_price_by_freshness_and_tip(self):
        with Workdir() as w:
            stock = items("ca_linh", "ca_linh", "ca_linh", "bong_dien_dien", fresh=60)
            stock[0]["fresh"] = 90
            sc = quan(stock, player={"pos": [2, 7]},
                      customers=[{"id": "C1", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien"}])
            rows = run(w, "quan", sc, inputs=[{"tick": 0, "interact": True}], ticks=1)
            cs = ev(rows, "cook_started")[0][1]
            total_u = (90 + 60 * 3) * U - 4  # 4 cá thể, mỗi cá thể hao 1 đơn vị ở bước 0
            self.assertEqual(cs["base_price"], math.floor(120 * total_u / (4 * U * 100)))
            self.assertEqual(ids_of(cs["items"]), ["I4", "I1", "I2", "I3"])  # sắp theo kind rồi id
        with Workdir() as w:
            hand = {"order_id": "C1", "dish_id": "lau_mam", "base_price": 153}
            sc = quan([], hand=hand, player={"pos": [9, 3]},
                      customers=[{"id": "C1", "table_id": "T1", "dish_id": "lau_mam", "order_status": "assigned"}])
            served = ev(run(w, "quan", sc, inputs=[{"tick": 0, "interact": True}], ticks=1), "served")[0][1]
            self.assertEqual((served["base_price"], served["tip"]), (153, math.floor(153 * 0.2)))

    def test_spoiled_not_used_for_orders(self):
        q_first = 120
        with Workdir() as w:
            rows = run(w, "quan", {"quan": {"stock": items("ca_loc", fresh=10)}}, ticks=q_first, every=q_first)
            self.assertEqual(ev(rows, "no_dish"), [(q_first, {})])
            self.assertEqual(len(snapshots(rows)[-1]["stock"]), 1, "hàng ươn vẫn nằm trong kho")

    def test_reserved_ids_scenario_conflicts_exit_2(self):
        with Workdir() as w:
            for sc in (quan(items("ca_loc"), customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I9"]}]),
                       quan(items("bong_sung"), customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}]),
                       quan(items("ca_loc"), customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": {"ca_loc": 1}}])):
                self.assertIsNone(run(w, "quan", sc, ticks=0, expect=2), sc)


class DayIds(unittest.TestCase):
    def test_ids_continue_across_days_and_template_new_ids(self):
        dur = 10800
        k = 1 + dur
        inputs = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                  {"tick": k, "shop_done": True}, {"tick": k + 1, "shop_done": False, "interact": True},
                  {"tick": k + 2, "interact": False}]
        with Workdir() as w:
            sc = {"gather": dict(QUIET, hold=[{"id": "I5", "kind": "ca_loc", "fresh": 70}])}
            rows = run(w, "day", sc, inputs=inputs, ticks=k + 2, every=100000, extra=("--days", "2"))
            starts = [r for r in snapshots(rows) if r["phase"] == "gather" and r["phase_tick"] == 0]
            self.assertEqual(starts[0]["hold"], [{"id": "I5", "kind": "ca_loc", "fresh": 70}])
            self.assertEqual(starts[1]["hold"], [{"id": "I6", "kind": "ca_loc", "fresh": 70}])  # id mới, kind/fresh ban đầu
            shop = [r for r in snapshots(rows) if r["phase"] == "shop"][0]
            self.assertEqual(ids_of(shop["stock"]), ["I5"])  # hàng thô ở Shop

    def test_day_hold_instance_schema_checked(self):
        with Workdir() as w:
            self.assertIsNone(run(w, "day", {"gather": {"hold": ["ca_loc"]}}, ticks=0, expect=2))


if __name__ == "__main__":
    unittest.main()

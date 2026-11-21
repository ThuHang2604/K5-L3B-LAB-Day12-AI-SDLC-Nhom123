"""Test luật `quan` của nhóm (hộp đen qua headless). Mọi số đọc từ game.contract.json."""

import json
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    _C = json.load(_f)["tuning"]
Q, MENU = _C["quan"], _C["menu"]
TICK = 60
SEC = lambda s: int(round(s * TICK))  # noqa: E731
STOVE, TABLE = Q["stoves"][0], Q["tables"][0]


def run(w, block, fr, ticks, seed=1, extra=()):
    sc = write_json(w.path("sc.json"), {"quan": block})
    inp = write_json(w.path("in.json"), frames(*fr))
    code, err = run_headless("--mode", "quan", "--seed", str(seed), "--ticks", str(ticks), "--scenario", sc,
                             "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"), *extra)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def names(rows):
    return [r["name"] for r in events(rows)]


CUSTOMER = {"id": "C1", "table_id": TABLE["id"], "dish": "ca_loc_nuong_trui"}
STOCK = {"ca_loc": 1}


class Arrivals(unittest.TestCase):
    def test_first_customer_at_scheduled_tick_with_cookable_dish(self):
        with Workdir() as w:
            rows = run(w, {"stock": {"bong_sung": 2}}, [], Q["first_customer_tick"] + 2)
            arr = events(rows, "customer_arrived")
            self.assertEqual(len(arr), 1)
            self.assertEqual(arr[0]["tick"], Q["first_customer_tick"])
            self.assertEqual(arr[0]["data"]["dish"], "goi_bong_sung")  # món duy nhất nấu được
            c = snapshots(rows)[-1]["customers"][0]
            self.assertEqual(c["reserved"], {"bong_sung": 2})
            self.assertEqual(c["id"], "C1")

    def test_no_dish_when_stock_empty(self):
        with Workdir() as w:
            rows = run(w, {"stock": {}}, [], Q["first_customer_tick"] + 1)
            self.assertEqual(len(events(rows, "no_dish")), 1)
            self.assertEqual(snapshots(rows)[-1]["customers"], [])

    def test_second_customer_after_interval_and_reservation(self):
        """Quán chỉ có 1 bàn: khách thứ hai (sau customer_interval_s) không vào khi bàn còn bận."""
        with Workdir() as w:
            ticks = Q["first_customer_tick"] + SEC(Q["customer_interval_s"]) + 1
            rows = run(w, {"stock": STOCK}, [], ticks)
            self.assertEqual(len(events(rows, "customer_arrived")), 1)

    def test_random_customers_false_disables_schedule(self):
        with Workdir() as w:
            rows = run(w, {"stock": STOCK, "random_customers": False}, [], Q["first_customer_tick"] + 5)
            self.assertEqual(events(rows, "customer_arrived") + events(rows, "no_dish"), [])


class Lifecycle(unittest.TestCase):
    def test_cook_pick_serve_pay_with_tip(self):
        """Bàn đặt sát bếp để một người đi tới cả hai: nấu -> chín -> lấy món -> phục vụ -> ăn -> trả tiền + boa."""
        cook, eat = SEC(MENU["ca_loc_nuong_trui"]["cook_s"]), SEC(Q["eat_s"])
        sx, sz = STOVE["pos"]
        block = {"stock": STOCK, "customers": [CUSTOMER], "random_customers": False,
                 "player": {"pos": [sx, sz]}, "tables": [{"id": TABLE["id"], "pos": [sx + 1, sz]}]}
        fr = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False},          # bắt đầu nấu (đứng ở bếp)
              {"tick": cook + 2, "interact": True}, {"tick": cook + 3, "interact": False},  # lấy món
              {"tick": cook + 4, "move": [1, 0]}, {"tick": cook + 24, "move": [0, 0]},     # bước sang gần bàn hơn bếp
              {"tick": cook + 30, "interact": True}, {"tick": cook + 31, "interact": False}]  # phục vụ
        with Workdir() as w:
            rows = run(w, block, fr, cook + 30 + eat + 5)
        self.assertEqual(names(rows)[:5], ["cook_started", "dish_ready", "dish_picked", "served", "paid"])
        self.assertEqual(events(rows, "dish_ready")[0]["tick"], 1 + cook)
        paid = events(rows, "paid")[0]["data"]
        price = MENU["ca_loc_nuong_trui"]["price"]
        tip = int(round(price * Q["tip_rate"]))
        self.assertEqual((paid["price"], paid["tip"]), (price, tip))  # phục vụ nhanh -> còn đủ kiên nhẫn -> có boa
        last = snapshots(rows)[-1]
        self.assertEqual((last["money"], last["earned"]), (price + tip, price + tip))
        self.assertAlmostEqual(last["reputation"], Q["reputation_initial"] + Q["tip_reputation"])
        self.assertEqual(last["score"], price + tip + 100 * int(last["reputation"]))
        self.assertEqual((last["customers"], last["hand"], last["stock"]), ([], None, {}))

    def test_no_tip_when_patience_below_ratio(self):
        low = int(SEC(Q["patience_s"]) * Q["tip_min_patience_ratio"]) - 1
        with Workdir() as w:
            block = {"stock": {}, "random_customers": False,
                     "customers": [{**CUSTOMER, "state": "eating", "eat_ticks_left": 3, "patience_ticks": low}]}
            rows = run(w, block, [], 6)
        self.assertEqual(events(rows, "paid")[0]["data"]["tip"], 0)
        self.assertEqual(snapshots(rows)[-1]["reputation"], Q["reputation_initial"])

    def test_tip_at_exact_ratio_boundary(self):
        edge = int(SEC(Q["patience_s"]) * Q["tip_min_patience_ratio"])
        with Workdir() as w:
            block = {"stock": {}, "random_customers": False,
                     "customers": [{**CUSTOMER, "state": "eating", "eat_ticks_left": 2, "patience_ticks": edge}]}
            rows = run(w, block, [], 4)
        self.assertGreater(events(rows, "paid")[0]["data"]["tip"], 0)

    def test_serve_wrong_dish_does_nothing(self):
        with Workdir() as w:
            block = {"stock": STOCK, "hand": "goi_bong_sung", "random_customers": False,
                     "customers": [CUSTOMER], "player": {"pos": TABLE["pos"]}}
            rows = run(w, block, [{"tick": 0, "interact": True}], 3)
        self.assertNotIn("served", names(rows))
        self.assertEqual(snapshots(rows)[-1]["hand"], "goi_bong_sung")

    def test_only_one_interact_per_tick_stove_before_table(self):
        """Đứng sát cả bếp và bàn, khoảng cách bằng nhau: bếp được chọn trước, bàn không bị xử lý cùng tick."""
        sx, sz = STOVE["pos"]
        block = {"stock": STOCK, "hand": None, "random_customers": False, "customers": [CUSTOMER],
                 "player": {"pos": [sx, sz]}, "tables": [{"id": TABLE["id"], "pos": [sx, sz]}]}
        with Workdir() as w:
            rows = run(w, block, [{"tick": 0, "interact": True}], 2)
        self.assertEqual(names(rows), ["cook_started"])


class Patience(unittest.TestCase):
    def test_customer_leaves_when_patience_runs_out_and_reputation_drops(self):
        with Workdir() as w:
            block = {"stock": STOCK, "random_customers": False, "customers": [{**CUSTOMER, "patience_ticks": 5}]}
            rows = run(w, block, [], 10)
            left = events(rows, "customer_left")
            self.assertEqual(len(left), 1)
            self.assertEqual(left[0]["tick"], 5)
            last = snapshots(rows)[-1]
            self.assertAlmostEqual(last["reputation"], Q["reputation_initial"] + Q["left_reputation_delta"])
            self.assertEqual(last["customers"], [])

    def test_reputation_clamped_at_min(self):
        with Workdir() as w:
            block = {"stock": STOCK, "random_customers": False, "reputation": 0.2,
                     "customers": [{**CUSTOMER, "patience_ticks": 2}]}
            rows = run(w, block, [], 5)
            self.assertEqual(snapshots(rows)[-1]["reputation"], Q["reputation_min"])

    def test_reservation_released_when_customer_leaves(self):
        with Workdir() as w:
            # khách 1 sắp bỏ đi (giữ chỗ cá lóc); sau khi đi, khách mới đến lúc first_customer_tick nấu được món đó
            block = {"stock": STOCK, "customers": [{**CUSTOMER, "patience_ticks": 3}]}
            rows = run(w, block, [], Q["first_customer_tick"] + 1)
            arr = events(rows, "customer_arrived")
            self.assertEqual(arr[0]["data"]["dish"], "ca_loc_nuong_trui")

    def test_burn_not_in_phase_1(self):
        # burn_s = null: món để chín không cháy
        cook = SEC(MENU["ca_loc_nuong_trui"]["cook_s"])
        with Workdir() as w:
            block = {"stock": STOCK, "customers": [CUSTOMER], "random_customers": False,
                     "player": {"pos": STOVE["pos"]}}
            rows = run(w, block, [{"tick": 0, "interact": True}], cook + 200)
            self.assertEqual(snapshots(rows)[-1]["stoves"][0]["state"], "ready")


class Scenario(unittest.TestCase):
    def test_assigned_without_dish_exit_2(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"customers": [{"id": "C1", "table_id": "T1"}]}})
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc,
                                          "--out", w.path("o.jsonl"))[0], 2)

    def test_reserved_more_than_stock_exit_2(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"stock": {}, "customers": [CUSTOMER]}})
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc,
                                          "--out", w.path("o.jsonl"))[0], 2)
            inv = write_json(w.path("inv.json"), {"items": {}})
            sc = write_json(w.path("sc2.json"), {"quan": {"customers": [CUSTOMER]}})
            self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc,
                                          "--inventory", inv, "--out", w.path("o.jsonl"))[0], 2)

    def test_bad_hand_and_reputation_exit_2(self):
        with Workdir() as w:
            for block in ({"hand": "pizza"}, {"reputation": 9}, {"customers": [{**CUSTOMER, "state": "dancing"}]}):
                sc = write_json(w.path("sc.json"), {"quan": block})
                self.assertEqual(run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc,
                                              "--out", w.path("o.jsonl"))[0], 2, block)


class EndOfShift(unittest.TestCase):
    def test_quan_end_event_and_row(self):
        with Workdir() as w:
            rows = run(w, {"stock": {}, "time_left_ticks": 4}, [], 50)
            end = events(rows, "quan_end")
            self.assertEqual(len(end), 1)
            self.assertEqual(end[0]["tick"], 4)
            self.assertEqual(rows[-1]["reason"], "time")


class Determinism(unittest.TestCase):
    def test_same_seed_same_bytes_and_seed_matters_only_for_dish_choice(self):
        stock = {"ca_loc": 1, "bong_sung": 2}
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"stock": stock}})
            for i, seed in ((1, 3), (2, 3)):
                self.assertEqual(run_headless("--mode", "quan", "--seed", str(seed), "--ticks", "400", "--scenario", sc,
                                              "--out", w.path(f"o{i}.jsonl"))[0], 0)
            with open(w.path("o1.jsonl"), "rb") as a, open(w.path("o2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()

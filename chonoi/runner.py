"""Vòng tick (Contract B/E/F + v1.1 mục 4.2 pause, 4.4 output).

Thứ tự ghi: event dựng lượt (day) -> snapshot tick 0 -> với mỗi bước: event (theo thứ tự xử lý) rồi snapshot
(nếu tới lượt, đổi pha hoặc lượt kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

Ba bộ đếm: `tick` (bước ngoài, luôn tăng), `sim_tick` (bước gameplay toàn lượt, đứng yên khi pause),
`phase_tick` (bước gameplay trong pha hiện tại, do sim giữ).

`Session` là API bước tick dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`).
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    if mode == "day":
        return DaySim(tuning, scenario, streams, ids, days=days)
    return QuanSim(tuning, scenario, streams, ids, inventory=inventory)


class Session:
    """Một lượt chơi: dựng sim, bước từng tick (kể cả pause), lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False
        self.phase_changed = False
        self.initial_events = [self._row(e) for e in getattr(self.sim, "initial_events", [])]

    @property
    def done(self) -> bool:
        return self.sim.done

    @property
    def phase(self):
        return self.sim.phase

    def _state(self):
        if self.sim.done:
            return "finished"
        return "paused" if self.paused else "playing"

    def score(self):
        return self.sim.earned + self.tuning["score"]["reputation_multiplier"] * math.floor(self.sim.reputation)

    def snapshot(self) -> dict:
        s = {"type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "mode": self.mode,
             "phase": self.sim.phase, "phase_tick": self.sim.phase_tick, "state": self._state(),
             "time_left_ticks": self.sim.time_left_ticks, "money": self.sim.money, "earned": self.sim.earned,
             "reputation": self.sim.reputation, "score": self.score()}
        s.update(self.sim.snapshot())
        return s

    def _row(self, e):
        name, data = e[0], e[1]
        phase = e[2] if len(e) > 2 else self.sim.phase
        row = {"type": "event", "tick": self.tick, "phase": phase}
        if self.mode == "day":
            row["day"] = self.sim.day
        row.update(name=name, data=data)
        return row

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        before = (self.sim.phase, getattr(self.sim, "day", None))
        out = []
        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                self.tick += 1
                return [self._row(("paused", {}))]
            self.paused = False
            out.append(("resumed", {}))
        elif self.paused:
            self.tick += 1
            return []
        day_before = getattr(self.sim, "day", None)
        events = self.sim.step(inp)
        self.sim_tick += 1
        self.tick += 1
        rows = [self._row(e) for e in out + events]
        if self.mode == "day" and day_before != self.sim.day:
            # Shop đóng dựng Ngày mới cùng tick: các event trước day_start mang Ngày cũ
            seen_new = False
            for row in rows:
                if row["name"] == "day_start":
                    seen_new = True
                row["day"] = self.sim.day if seen_new else day_before
        self.phase_changed = (self.sim.phase, getattr(self.sim, "day", None)) != before
        return rows

    def end_row(self) -> dict:
        sim = self.sim
        row = {"type": "end", "ticks": self.tick, "sim_tick": self.sim_tick, "mode": self.mode,
               "state": self._state(), "reason": sim.reason if sim.done else "tick_limit",
               "money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": self.score()}
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None, inventory_out=None,
        days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days)  # BadInput ở đây: chưa ghi gì
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        for row in sess.initial_events:
            w.write(row)
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            if sess.tick % snapshot_every == 0 or sess.done or sess.phase_changed:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim

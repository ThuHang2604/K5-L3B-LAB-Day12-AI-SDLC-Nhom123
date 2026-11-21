"""Độ tươi cá thể (Test Contract v1.2).

Tính bằng số nguyên `UNITS` đơn vị mỗi điểm tươi để so ngưỡng 30 và phép floor chính xác:
gather 0.5/s = 2 đơn vị/tick, quán 0.25/s = 1 đơn vị/tick ở 60 Hz.
Cá thể nội bộ: {"id", "kind", "u"}; xuất ra JSON: {"id", "kind", "fresh"}.
"""

import math
from fractions import Fraction

from .ids import id_key

UNITS = 240


def to_units(fresh):
    u = fresh * UNITS
    r = round(u)
    return int(r) if abs(u - r) < 1e-6 else u


def per_tick_units(per_s):
    return to_units(per_s / 60.0)


def export(item) -> dict:
    return {"id": item["id"], "kind": item["kind"], "fresh": item["u"] / UNITS}


def export_sorted(items) -> list:
    return [export(i) for i in sorted(items, key=lambda i: id_key(i["id"]))]


def from_json(items) -> list:
    return [{"id": i["id"], "kind": i["kind"], "u": to_units(i["fresh"])} for i in items]


def new_item(ids, kind, tuning):
    return {"id": ids.new("I"), "kind": kind, "u": to_units(tuning["freshness"]["initial"])}


def threshold(tuning):
    return to_units(tuning["freshness"]["spoiled_below"])


def decay(items, per_tick, thr, location, events):
    """Hao tươi, kẹp 0; phát spoiled theo id khi đi từ ≥ ngưỡng xuống < ngưỡng. Trả id vừa ươn."""
    spoiled = []
    for it in sorted(items, key=lambda i: id_key(i["id"])):
        before = it["u"]
        it["u"] = max(0, it["u"] - per_tick)
        if before >= thr > it["u"]:
            spoiled.append(it["id"])
            events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": location}))
    return spoiled


def fresh_price(price, items) -> int:
    """floor(giá niêm yết × trung bình fresh / 100), tính bằng phân số chính xác."""
    if not items:
        return price
    total = sum(Fraction(i["u"]) for i in items)
    return math.floor(Fraction(price) * total / (len(items) * UNITS * 100))

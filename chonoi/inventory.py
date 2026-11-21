"""File kho v1.2 (TICKET-03): {"items": [{"id", "kind", "fresh"}, ...]} — kho CÁ THỂ.

Đọc: chọn schema theo contract_version; v1.2 từ chối kho đếm (object), kind lạ, id trùng/rỗng,
fresh ngoài [0, 100] (BadInput -> mã 2).
Ghi: sắp theo id, đủ độ chính xác (không làm tròn), qua file tạm cùng thư mục rồi thay thế nguyên tử.
"""

import math

import json
import os
import tempfile

from .errors import BadInput

KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung")


def kinds_from_tuning(tuning) -> tuple:
    """Mọi nguyên liệu hợp lệ = nguyên liệu xuất hiện trong công thức thực đơn (đọc từ contract)."""
    ks = set()
    for d in tuning["menu"].values():
        ks |= set(d["recipe"])
    return tuple(sorted(ks))


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def validate_instances(items, kinds, where="items"):
    if not isinstance(items, list):
        raise BadInput(f"{where} phải là mảng cá thể {{id,kind,fresh}} (kho đếm không còn hợp lệ ở v1.2)")
    seen = set()
    for it in items:
        if not isinstance(it, dict) or set(it) != {"id", "kind", "fresh"}:
            raise BadInput(f"{where}: mỗi cá thể đúng ba khóa id, kind, fresh")
        if not isinstance(it["id"], str) or not it["id"] or it["id"] in seen:
            raise BadInput(f"{where}: id phải là chuỗi khác rỗng, duy nhất ({it['id']!r})")
        seen.add(it["id"])
        if it["kind"] not in kinds:
            raise BadInput(f"{where}: nguyên liệu lạ {it['kind']!r}")
        f = it["fresh"]
        if isinstance(f, bool) or not isinstance(f, (int, float)) or not math.isfinite(f) or not (0 <= f <= 100):
            raise BadInput(f"{where}: fresh của {it['id']} phải hữu hạn trong [0, 100]")
    return items


def read_inventory(path: str, kinds=KINDS_P1) -> list:
    """Đọc kho cá thể v1.2, trả danh sách {id,kind,fresh}."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_instances(data["items"], kinds)


def read_inventory_counts(path: str, kinds=KINDS_P1) -> dict:
    """Kho đếm v1.0/v1.1 (giữ cho tham khảo; v1.2 không dùng)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> dict:
    """Khoang (mảng id theo thứ tự nhặt) -> object đếm, sắp theo id nguyên liệu."""
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items: list):
    """items: danh sách cá thể đã xuất {id,kind,fresh}, đã sắp theo id."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": list(items)}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

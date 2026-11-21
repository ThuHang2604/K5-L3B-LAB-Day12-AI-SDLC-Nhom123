# Kế hoạch Phase 3 — Change Request "Mùa Nước Nổi" (v1.2)

Quyết định schema: [ADR 0001](../adr/0001-kho-ca-the-v1-2.md). Thứ tự tích hợp: adapter/schema + migrate test → Lặn → Quán → day → HUD → proof.

## Phân tích tác động

| Module | File cần đổi | Test bị ảnh hưởng | Người phụ trách |
|---|---|---|---|
| Adapter / schema | `chonoi/fresh.py` (mới), `chonoi/inventory.py`, `chonoi/contract.py`, `game.contract.json`, `chonoi/scenario.py` | đổi: `test_smoke_p1.Integration.*`, `test_python_starter_units`; thêm: `test_rules_p3.Handoff.*` | Hằng |
| Lặn | `chonoi/sim/gather.py` | đổi: `test_rules_p1.Oxygen/Harvest/Catch`, `test_rules_p2.Monster` (lost là mảng cá thể); thêm: `test_rules_p3.Threshold.*` | Linh |
| Quán | `chonoi/sim/quan.py` | đổi: `test_rules_p1.Quan.*` (giá theo tươi), `test_rules_p2.QuanV11/Pause`; thêm: `test_rules_p3.QuanFresh.*` | Vinh |
| day | `chonoi/sim/day.py` | đổi: `test_rules_p2.Day.*`; thêm: `test_rules_p3.DayIds.*` | Hằng |
| HUD | `chonoi/web/index.html`, `chonoi/live.py`, `tools/ui_shots.py` | `test_live` giữ nguyên | Dung |
| QA / docs | `tools/proof.sh`, `docs/*`, `CHANGELOG.md`, `README.md` | — | Hằng + Linh (tag) |

## Mở rộng
Nhóm 4 người: không làm `current`/`reservations` (không bắt buộc), `extensions` vẫn rỗng.

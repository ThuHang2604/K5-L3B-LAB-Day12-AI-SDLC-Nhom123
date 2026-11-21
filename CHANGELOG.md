# Changelog
## phase-4 — v1.0.0 (Test Contract v1.3)
- Manifest `contract_version: "1.3"`, thêm `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`); gameplay, tuning, kho, JSONL giữ v1.2.
- Benchmark có render cảnh lặn 1280×720 (trình duyệt hoặc renderer phần mềm), soak 10 Ngày bằng bot tất định (kế hoạch D1–D5 lặp).
- Cảnh báo chữ + biểu tượng (thủy quái gần, sắp hết oxy, khách sắp giận), chế độ tương phản cao (phím H).
- Sửa: uy tín làm tròn 9 chữ số sau mỗi lần đổi để floor(uy tín) không lệch do cộng dồn số thực.
- Phát hành: README 3 lệnh từ clone sạch, release notes, LICENSE (MIT), CREDITS, `tools/package.sh`.

## phase-3 — Test Contract v1.2 "Mùa Nước Nổi" (BREAKING)
- **Breaking:** file kho đổi từ kho đếm `{"items":{"ca_loc":1}}` sang kho cá thể `{"items":[{"id":"I1","kind":"ca_loc","fresh":97.5}]}`. Bản v1.2 trả mã 2 cho kho đếm.
- **Breaking (scenario):** `gather.hold`, `quan.stock` là mảng cá thể; `customers[].reserved` là mảng id cá thể; payload món giữ cấu trúc, `base_price` là giá đã chốt theo tươi.
- **Breaking (JSONL):** `hold`, `stock` (quán, Shop), `cook_started.items`, `lost` là cá thể; event mới `spoiled {item_id, kind, location}`.
- Mới: độ tươi (giỏ −0.5/s, kho −0.25/s, ươn < 30), giữ chỗ tươi nhất theo id, thử giữ lại khi hàng vừa ươn, giá theo độ tươi; HUD hiện độ tươi/ươn.
- Cập nhật fixture: thay `"hold": ["ca_loc"]` bằng `"hold": [{"id":"I1","kind":"ca_loc","fresh":100}]`; thay `"stock": {"ca_loc": 2}` bằng hai cá thể; thay `"reserved": {"ca_loc":1}` bằng `"reserved": ["I1"]`. Trong test dùng `helpers.items("ca_loc", "ca_loc")`.

## phase-2
- Test Contract v1.1: số chuẩn, cá bơi/sinh, Cá Sấu Năm Chèo, 2 bếp/4 bàn, 6 món, `--mode day` với kế hoạch D1–D5 và Shop nâng cấp, pause.
- UI vòng ngày: menu, DayIntro, EveningIntro, DayResult, Shop, Tổng kết, pause, HUD đầy đủ.
## phase-1
- Lõi gather (oxy, ngạt, ngất, hái, bắt cá) và quán (khách, giữ chỗ, bếp, phục vụ, tiền, uy tín) theo Test Contract v1.0.

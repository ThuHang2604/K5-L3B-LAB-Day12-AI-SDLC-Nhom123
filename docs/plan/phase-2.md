# Kế hoạch Phase 2 (TICKET-02, Test Contract v1.1)

- Mục tiêu: thay số chuẩn, chơi trọn vòng ngày (day/Shop/pause/menu/HUD), regression P1 còn xanh; tag `phase-2` trước 1:55.
- Giao diện chuyển pha chốt ở phút 0–5: `DaySim` giữ tiền/uy tín/cấp; `GatherSim(day, oxygen_max_s, hp_max)` và `QuanSim(inventory, menu_ids)` nhận trạng thái qua tham số; event đổi pha do `DaySim` phát; UI đọc `ui_hold`.

| Việc | AC | Người | Phụ thuộc |
|---|---|---|---|
| (1) Số chuẩn + cá bơi/sinh | AC-P2-01..03 | Linh | contract v1.1 |
| (2) Cá Sấu, Máu, ngất | AC-P2-04..06 | Linh | (1) vị trí người chơi sau bơi |
| (3) 2 bếp/4 bàn, 6 món, lọc kế hoạch | AC-P2-07..08 | Vinh (inputs/CLI, lọc món theo kế hoạch đi qua day) | contract v1.1 |
| (4) day, Shop, pause, menu, HUD | AC-P2-09..14 | Hằng (day/Shop/pause) + Dung (menu, HUD) | fixture cố định để tích hợp sớm |

- Rủi ro: thứ tự hit/ngạt/hết giờ cùng tick; số thực khi Cá Sấu tới waypoint (đã thêm dung sai 1e-9); day dài 22.200 tick phải ≤ 20 s (đo được 0.47 s).

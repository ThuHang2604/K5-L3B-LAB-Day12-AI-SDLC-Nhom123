# Ma trận truy vết Phase 2 (Test Contract v1.1)

Chạy `bash tools/proof.sh 2` trên commit bàn giao → [`docs/proof/phase-2/`](../proof/phase-2/). Kết quả test: [`tests.txt`](../proof/phase-2/tests.txt) (75 test, `RESULT: PASS`), commit ghi ở [`env.txt`](../proof/phase-2/env.txt) là commit code ngay trước commit tài liệu gắn tag (hai commit chỉ khác `docs/`, `README.md`, `CHANGELOG.md`, `AGENTS.md`).

| AC | Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P2-01 | `contract_version 1.1`, số chuẩn, 6 nguyên liệu, 6 món, N5/N6, B2, T2–T4, `day_plan` = Σ công thức × suất | `test_rules_p2.Manifest`, `chonoi/contract.py` kiểm khi nạp | tests.txt | Đạt |
| AC-P2-02 | 8 đàn đầu ca ở 8 điểm sinh khác nhau; bơi 1.5 m/s trong dải loài; phản xạ mép; đổi hướng ở bước bơi 120·k | `Fish.test_initial_*`, `test_swim_speed_*`, `test_reflect_*`, `test_turn_*` | tests.txt | Đạt |
| AC-P2-03 | Sinh 1 đàn tại 360·k nếu < 12, trọng số loài, `fish_spawned`; `random_fish:false` đứng yên | `Fish.test_spawn_schedule_and_cap`, `test_random_fish_false_static` | tests.txt | Đạt |
| AC-P2-04 | Cá Sấu patrol 1 m/s giữa 2 waypoint, chase 3 m/s khi d ≥ 10 và ≤ 10 m, M2 từ Ngày 3 | `Monster.test_default_layout_day1`, `test_patrol_*`, `test_chase_*`, `Day.test_five_days_*` | tests.txt | Đạt |
| AC-P2-05 | Chạm: −1 Máu, rơi floor(n/2) LIFO, bất tử 90, recoil 60 bước lùi 2 m; không hit khi bất tử/nông | `Monster.test_hit_*`, `test_no_hit_*` | tests.txt | Đạt |
| AC-P2-06 | Ngất do quái/ngạt: `faint` (lost = phần còn lại LIFO) → `gather_end fainted`, quán vẫn mở kho rỗng; ngạt xuyên bất tử, không rơi hàng | `Monster.test_faint_by_monster_keeps_order`, `test_choke_ignores_invuln_*` | tests.txt | Đạt |
| AC-P2-07 | 2 bếp/4 bàn: bàn trống id nhỏ, bếp lấy đơn cũ nhất (order_tick → id bàn), lịch 120 + 900k | `QuanV11.*` | tests.txt | Đạt |
| AC-P2-08 | Trong day, khách chỉ gọi món của kế hoạch; quán riêng dùng cả 6 món | `Day.test_day_menu_filtered_by_plan`, `QuanV11.test_standalone_*` | tests.txt | Đạt |
| AC-P2-09 | `--mode day`: day_start → day_plan → phase_start; đổi pha cùng tick, snapshot pha mới `phase_tick 0`; event kết thúc mang pha cũ | `Day.test_day_start_order_*`, `test_phase_changes_*` | tests.txt, [day1.jsonl](../proof/phase-2/day1.jsonl) | Đạt |
| AC-P2-10 | Công bố đúng kế hoạch D1–D5, chốt Ngày khi Shop đóng, `days_complete` | `Day.test_five_days_plan_and_upgrades_next_day` | tests.txt | Đạt |
| AC-P2-11 | Shop: mua oxygen/hp, `buy_failed` funds/max_level/unknown, tự đóng 600 tick; cấp áp dụng từ Ngày kế | `Day.test_shop_*`, `tools/proof_days.py` | [days-upgrades.txt](../proof/phase-2/days-upgrades.txt) | Đạt |
| AC-P2-12 | Pause: `paused`/`resumed`, sim_tick/phase_tick/timer đứng yên, cạnh hành động trong pause bị bỏ | `Pause.*` | tests.txt | Đạt |
| AC-P2-13 | Smoke tích hợp gather `--inventory-out` → quan `--inventory`, stock tick 0 khớp | `tools/proof.sh` | [integration-check.txt](../proof/phase-2/integration-check.txt) | Đạt |
| AC-P2-14 | Regression P1 với số chuẩn | `test_smoke_p1`, `test_rules_p1` chạy lại | tests.txt | Đạt (2 test starter đổi có lý do, xem dưới) |
| AC-P2-15 | Headless 1 Ngày (22.200 tick) ≤ 20 s; tất định từng byte | `Day.test_day_one_runs_under_20s`, `Determinism.*`, `cmp` | [day-timing.txt](../proof/phase-2/day-timing.txt) (0.47 s), [determinism.txt](../proof/phase-2/determinism.txt) | Đạt |
| AC-P2-16 | Menu Chơi/Thoát, DayIntro tự chuyển 4 s, EveningIntro, DayResult, Shop, Summary, pause Esc/P làm mờ nền | Chrome headless `tools/ui_shots.py` + `test_live.LiveDayFlow` | [ui/](../proof/phase-2/ui/) (9 ảnh) | Đạt |
| AC-P2-17 | HUD sáng/tối đủ mục, chữ ≥ 18 px ở 1280×720; ≥ 30 FPS | Ảnh chụp 1280×720; đo `requestAnimationFrame` 2 s | ui/3-gather.png, ui/6-quan.png; FPS đo 60 | Đạt |

## Test cũ đổi vì luật mới
- `test_smoke_p1.test_gather_snapshot_has_gather_fields`: số đàn đầu ca đọc từ `fish_initial` (v1.1 = 8, v1.0 là danh sách 6).
- `test_smoke_p1.test_con_03_old_and_future_modes_rejected`: bỏ `day` khỏi danh sách mode bị từ chối vì v1.1 đã có `--mode day`.

## Đánh giá ngắn
- Đạt: toàn bộ lõi v1.1 headless + vòng ngày chơi được trên trình duyệt.
- Hạn chế: chưa làm mở rộng (nhóm 4 người không bắt buộc); âm thanh chưa có.

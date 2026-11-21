# Ma trận truy vết Phase 1 (Test Contract v1.0)

Chạy trên commit gắn tag `phase-1`: `bash tools/proof.sh 1` → [`docs/proof/phase-1/`](../proof/phase-1/). Test: [`tests.txt`](../proof/phase-1/tests.txt) (`RESULT: PASS`).

| AC | Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P1-01 | Bơi 4 m/s, ramp ≤ 6 tick, chặn biên, d không âm, hướng 90° = xuống | `test_smoke_p1.Movement.*` | tests.txt | Đạt |
| AC-P1-02 | Oxy −1/+6, `oxygen_empty`, ngạt lần đầu t+59, reset khi nổi | `test_rules_p1.Oxygen.*` | tests.txt | Đạt |
| AC-P1-03 | Máu 0 → `faint` (lost LIFO) → `gather_end fainted`, kho rỗng | `Oxygen.test_ac_faint_drops_hold_lifo_and_empty_inventory` | tests.txt | Đạt |
| AC-P1-04 | Hái ở mặt nước, đúng mép bán kính, hòa theo id, mọc lại 20 s, `hold_full` | `test_rules_p1.Harvest.*` | tests.txt | Đạt |
| AC-P1-05 | Bắt cá dưới nước, đàn gần nhất, yield, hồi 30 tick, thiếu chỗ không hồi | `test_rules_p1.Catch.*` | tests.txt | Đạt |
| AC-P1-06 | Cập bến / hết giờ giữ giỏ, ghi kho đúng một lần, `--ticks` sớm không ghi | `test_smoke_p1.Integration.*`, `Movement.test_time_ends_gather_and_keeps_hold` | tests.txt | Đạt |
| AC-P1-07 | Khách tick 120 + mỗi 15 s, bàn trống id nhỏ, giữ chỗ khi gọi, `no_dish` | `Quan.test_ac_customer_schedule_reserve_and_no_dish` | tests.txt | Đạt |
| AC-P1-08 | Hết kiên nhẫn → rời, −0.5 uy tín, nhả giữ chỗ | `Quan.test_ac_patience_left_reputation` | tests.txt | Đạt |
| AC-P1-09 | Nấu (tiêu nguyên liệu giữ) → chín → bưng → phục vụ → ăn → trả tiền + boa | `Quan.test_ac_full_order_cook_pick_serve_pay_tip`, `test_no_tip_below_half_patience` | tests.txt | Đạt |
| AC-P1-10 | Hết ca: khách ăn trả `closing`, khách chờ rời không trừ uy tín, `quan_end` | `Quan.test_closing_pays_eating_and_releases_waiting` | tests.txt | Đạt |
| AC-P1-11 | Fixture mâu thuẫn / sai schema → mã 2 trước khi ghi JSONL | `Quan.test_scenario_conflicts_exit_2`, `test_smoke_p1.Contract.*` | tests.txt | Đạt |
| AC-P1-12 | Smoke hai tiến trình: quán tick 0 có `stock {"bong_sung":2,"ca_loc":1}` | `tools/proof.sh` | [integration-check.txt](../proof/phase-1/integration-check.txt), [integration-catch.json](../proof/phase-1/integration-catch.json) | Đạt |
| AC-P1-13 | Tất định: cùng seed/đầu vào → JSONL giống từng byte | `Contract.test_con_02_deterministic_bytes` + `cmp` | [determinism.txt](../proof/phase-1/determinism.txt) | Đạt |
| AC-P1-14 | HUD đọc được: thời gian, oxy, Máu, giỏ / kho, món, kiên nhẫn, bếp, tay, tiền, uy tín | Chơi thử `python3 -m chonoi.live` (cửa sổ starter đọc snapshot) | chơi tay | Đạt mức tối thiểu (hình khối) |

## Đánh giá ngắn
- Đạt: toàn bộ lõi headless theo Test Contract v1.0, smoke hai tiến trình, tất định.
- Chưa đạt / hạn chế: HUD vẫn là hình khối của starter; TEAM.md đã đủ 4 thành viên.
- Cho phase sau: tách số liệu cá bơi/quái vào contract, làm UI vòng ngày.

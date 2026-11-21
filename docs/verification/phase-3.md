# Ma trận truy vết Phase 3 (Test Contract v1.2 — kho cá thể + độ tươi)

`bash tools/proof.sh 3` → [`docs/proof/phase-3/`](../proof/phase-3/). Test: [`tests.txt`](../proof/phase-3/tests.txt) (`RESULT: PASS`). [`env.txt`](../proof/phase-3/env.txt) ghi commit code đã chạy (commit tài liệu gắn tag chỉ đổi `docs/`, `README.md`, `CHANGELOG.md`).

| AC | Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P3-01 | `contract_version 1.2`, khối `freshness {100, 0.5, 0.25, 30}` | `chonoi/contract.py` kiểm khi nạp; `Manifest.test_v11_standard_data` | tests.txt | Đạt |
| AC-P3-02 | File kho cá thể `{id,kind,fresh}`, sắp theo id, ghi một lần, nguyên tử, đủ chính xác | `Handoff.test_ac_p3_file_handoff_exact`, `test_file_keeps_branch_at_threshold` | [integration-check.txt](../proof/phase-3/integration-check.txt), [integration-catch.json](../proof/phase-3/integration-catch.json) | Đạt |
| AC-P3-03 | Kho đếm / id trùng / kind lạ / fresh ngoài miền → mã 2 | `Handoff.test_count_schema_and_bad_instances_exit_2`, `test_smoke_p1.test_inv_bad_schema_exit_2` | [threshold-check.txt](../proof/phase-3/threshold-check.txt) | Đạt |
| AC-P3-04 | Id I1, I2… theo thứ tự vào giỏ, tăng xuyên pha/Ngày; Ngày kế cấp id mới cho mẫu | `Threshold.test_new_item_fresh_100_ids_continue`, `DayIds.*` | tests.txt | Đạt |
| AC-P3-05 | Hàng mới 100, hao từ bước sau; giỏ −0.5/s, kho −0.25/s, kẹp 0; pause dừng hao | `Threshold.test_gather_decay_*`, `QuanFresh.test_stock_decay_quarter_per_second_and_pause` | tests.txt | Đạt |
| AC-P3-06 | `spoiled` đúng một lần khi qua ngưỡng 30, theo id, location hold/stock (fixture 30 → tick 1) | `Threshold.test_ac_p3_spoiled_exactly_at_30_in_hold`, `test_spoiled_once_and_by_id` | [threshold-gather.jsonl](../proof/phase-3/threshold-gather.jsonl) | Đạt |
| AC-P3-07 | Giữ chỗ theo id: tươi nhất rồi id; hàng ươn không dùng nấu | `QuanFresh.test_reserve_freshest_then_id_*`, `test_spoiled_not_used_for_orders` | tests.txt | Đạt |
| AC-P3-08 | Phần giữ vừa ươn: nhả toàn bộ, thử giữ lại đúng một lần; thiếu → unfulfillable | `QuanFresh.test_ac_p3_reserved_item_spoils_rereserve_once` | tests.txt | Đạt |
| AC-P3-09 | Giá chốt `floor(giá × fresh trung bình / 100)`, boa trên giá đã chốt; `cook_started.items` cá thể sắp kind rồi id | `QuanFresh.test_ac_p3_price_by_freshness_and_tip`, `Quan.test_ac_full_order_*` | tests.txt | Đạt |
| AC-P3-10 | `lost` của monster_hit/faint là mảng cá thể LIFO | `Monster.test_hit_*`, `test_faint_by_monster_*`, `Oxygen.test_ac_faint_*` | tests.txt | Đạt |
| AC-P3-11 | day: bàn giao cùng tick không hao thêm; Shop giữ hàng thô không hao | `Day.test_phase_changes_same_tick_and_snapshot`, `DayIds.*` | tests.txt, [day1.jsonl](../proof/phase-3/day1.jsonl) | Đạt |
| AC-P3-12 | Scenario v1.2: hold/stock mảng cá thể, reserved mảng id, mâu thuẫn → mã 2 | `QuanFresh.test_reserved_ids_scenario_conflicts_exit_2`, `Quan.test_scenario_conflicts_exit_2`, `DayIds.test_day_hold_instance_schema_checked` | tests.txt | Đạt |
| AC-P3-13 | HUD thấy độ tươi / hàng ươn | ô màu theo fresh trong giỏ (đỏ gạch chéo = ươn), "Kho khả dụng (độ tươi)", "+n ươn", "(hết hàng tươi)" ở bàn | [ui/](../proof/phase-3/ui/) | Đạt |
| AC-P3-14 | Regression P1–P2 còn hiệu lực với v1.2 | `test_smoke_p1`, `test_rules_p1`, `test_rules_p2` | tests.txt, [days-upgrades.txt](../proof/phase-3/days-upgrades.txt), [day-timing.txt](../proof/phase-3/day-timing.txt) | Đạt |

## Test đổi vì luật mới (TICKET-03 [THAY THẾ])
- Mọi fixture `hold`/`stock` chuyển sang mảng cá thể (`helpers.items(...)`); `reserved` thành mảng id.
- `test_smoke_p1.test_inv_01_*`: smoke bàn giao thay bằng phiên bản v1.2 trong ticket (so id/kind/fresh).
- `test_rules_p1.Quan.test_ac_full_order_*`: giá chốt theo tươi (kho hao 1 đơn vị trước khi nấu → 59 thay vì 60).
- `lost` so theo id/kind thay vì mảng kind.

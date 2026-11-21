# Ma trận truy vết Phase 4 (Test Contract v1.3 — phát hành v1.0.0)

`bash tools/proof.sh 4` → [`docs/proof/phase-4/`](../proof/phase-4/). Test: [`tests.txt`](../proof/phase-4/tests.txt) (`RESULT: PASS`). [`env.txt`](../proof/phase-4/env.txt) ghi commit code đã chạy (commit tài liệu gắn tag chỉ đổi `docs/`, `README.md`, `CHANGELOG.md`).

| AC | Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| AC-P4-01 | `contract_version 1.3`, `bench_cmd`, `soak_cmd` ở gốc manifest; gameplay/kho/JSONL theo v1.2 | `test_release_p4.ManifestV13`, regression P1–P3 | tests.txt | Đạt |
| AC-P4-02 | `bench_cmd --seed 42 --duration 30 --out bench.json` chạy cảnh buổi sáng lõi (độ tươi, cá bơi, Cá Sấu), Út Sen đứng yên ở bến, 1280×720, làm nóng 3 s, xuất đúng 5 trường | `tools/proof.sh 4`; `test_release_p4.Bench` (renderer software) | [bench.json](../proof/phase-4/bench.json), [bench-stderr.txt](../proof/phase-4/bench-stderr.txt) | Đạt — số đo trong bench.json (mốc báo cáo avg ≥ 60, 1% low ≥ 30, load ≤ 10 s) |
| AC-P4-03 | `soak_cmd --seed 7 --days 10`: days_completed = days, crashes = 0, results theo Ngày, lặp lại cùng seed cho cùng trường gameplay | `tools/proof.sh 4`; `test_release_p4.Soak` | [soak.json](../proof/phase-4/soak.json) | Đạt |
| AC-P4-04 | Clone sạch chạy giao diện bằng 3 lệnh theo README | `tools/proof.sh 4` clone repo, chạy `python3 -m chonoi.live`, đọc `/state`, chạy test trong clone | [clean-clone.txt](../proof/phase-4/clean-clone.txt) | Đạt |
| AC-P4-05 | Ba cảnh báo có chữ + biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận | Chụp bằng Chrome headless `tools/ui_shots_hc.py` | [ui/gather-monster-oxygen.png](../proof/phase-4/ui/gather-monster-oxygen.png), [ui/quan-angry.png](../proof/phase-4/ui/quan-angry.png) | Đạt |
| AC-P4-06 | Chế độ tương phản cao hoạt động, chơi thử cả ba cảnh báo ở chế độ đó | `?contrast=1` / phím H; ảnh chụp | [ui/gather-monster-oxygen-hc.png](../proof/phase-4/ui/gather-monster-oxygen-hc.png), [ui/quan-angry-hc.png](../proof/phase-4/ui/quan-angry-hc.png) | Đạt |
| AC-P4-07 | Regression P1–P3 còn hiệu lực | toàn bộ `tests/` | tests.txt, [integration-check.txt](../proof/phase-4/integration-check.txt), [threshold-check.txt](../proof/phase-4/threshold-check.txt), [days-upgrades.txt](../proof/phase-4/days-upgrades.txt), [day-timing.txt](../proof/phase-4/day-timing.txt), [determinism.txt](../proof/phase-4/determinism.txt) | Đạt |
| AC-P4-08 | CHANGELOG theo từng phase, release notes, LICENSE, CREDITS, bản đóng gói | `tools/package.sh v1.0.0` → `dist/quan-an-cho-noi-v1.0.0.zip` đính kèm GitHub Release | [CHANGELOG.md](../../CHANGELOG.md), [release notes](../release/v1.0.0.md), [LICENSE](../../LICENSE), [CREDITS.md](../../CREDITS.md) | Đạt (Release do Integrator công bố trên GitHub) |
| AC-P4-09 | Tag `phase-4` và Release v1.0.0 cùng trỏ một commit trên main | `git rev-parse phase-4` = commit của Release | trang Releases của repo | Integrator kiểm khi công bố |

## Test đổi vì luật mới
- `Manifest.test_v11_standard_data`: chấp nhận `contract_version` 1.2/1.3 (v1.3 chỉ thêm lệnh, gameplay giữ v1.2).
- Uy tín làm tròn 9 chữ số sau mỗi lần đổi (soak 10 Ngày lộ ra 3.4000000000000004; tránh floor(3.9999999) = 3).

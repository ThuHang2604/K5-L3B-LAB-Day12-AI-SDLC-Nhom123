# Kế hoạch Phase 4 — Phát hành v1.0.0 (Test Contract v1.3)

| Vai | Việc | Người | File |
|---|---|---|---|
| Bench/QA UI | `bench_cmd` (render 1280×720, trình duyệt hoặc software), cảnh báo chữ + biểu tượng, tương phản cao, ảnh chụp | Dung | `chonoi/bench.py`, `chonoi/web/index.html`, `chonoi/live.py`, `tools/ui_shots_hc.py` |
| Soak/QA | `soak_cmd` (bot tất định 10 Ngày, kế hoạch lặp), test P4, regression, ma trận phase-4 | Hằng | `chonoi/soak.py`, `chonoi/sim/day.py`, `tests/test_release_p4.py`, `tools/proof.sh`, `docs/verification/phase-4.md` |
| Đóng gói | thử clone sạch, README 3 lệnh, `tools/package.sh`, LICENSE, CREDITS | Vinh | `README.md`, `tools/package.sh`, `LICENSE`, `CREDITS.md`, `chonoi/sim/quan.py` (làm tròn uy tín) |
| Release/Integrator | manifest v1.3, release notes, CHANGELOG, tag `phase-4` + GitHub Release v1.0.0 | Linh | `game.contract.json`, `chonoi/contract.py`, `docs/release/v1.0.0.md`, `CHANGELOG.md` |
| Điều phối retro | rà hành động P2, tổng hợp bằng chứng đóng góp | Hằng | `docs/retro.md`, `TEAM.md` |

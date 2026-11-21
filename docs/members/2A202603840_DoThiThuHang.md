# ThuHang2604 — phản tư cá nhân (Đỗ Thị Thu Hằng, PO + QA lead)

- **Phần tôi làm:** P1 TEAM.md, `tests/test_rules_p1.py`, `tools/proof.sh`; P2 `chonoi/sim/day.py` + `chonoi/runner.py` (vòng ngày, Shop, pause), `tests/test_rules_p2.py`; P3 adapter kho cá thể (`chonoi/fresh.py`, `inventory.py`, ADR 0001), `test_rules_p3.py`; P4 `chonoi/soak.py`, `test_release_p4.py`, ma trận truy vết P1–P4 (xem `git log --author=ThuHang2604`).
- **Đã giúp ai:** viết helper `items(...)` để Linh và Vinh migrate fixture sang kho cá thể nhanh; chạy smoke tích hợp mỗi phase cho cả nhóm.
- **AI sai ở đâu:** P3 AI định so độ tươi bằng số thực — ví dụ ngưỡng 30 trong ticket lộ lỗi; chuyển sang 240 đơn vị/điểm và có test `test_file_keeps_branch_at_threshold`. P4 soak lộ uy tín cộng dồn 3.4000000000000004.
- **Bài học:** chốt hợp đồng + ADR và migrate test trước khi chia lát giúp main luôn chạy được.

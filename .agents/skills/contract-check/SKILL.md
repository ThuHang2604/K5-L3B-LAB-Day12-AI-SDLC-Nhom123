---
name: contract-check
description: Đối chiếu một thay đổi luật/manifest với Test Contract trước khi commit (số liệu chỉ ở game.contract.json, thứ tự bước, mã thoát 2, tất định).
---

Khi agent sửa `chonoi/sim/*`, `chonoi/scenario.py`, `chonoi/inputs.py` hoặc `game.contract.json`:
1. Mở mục F (thứ tự xử lý) của PRD/ticket phase hiện tại, so từng bước với hàm `step()` đã sửa.
2. Grep số "ma thuật" mới trong `chonoi/sim/` (`grep -nE '[^a-z_][0-9]{2,}' chonoi/sim/*.py`); số liệu phải đọc từ `tuning`.
3. Ngẫu nhiên chỉ qua `self.rng.get("<luồng>")`; không dùng `random`/`time` toàn cục.
4. Trường scenario/inputs mới: thêm vào tập khóa cho phép, trường lạ → mã 2 trước khi ghi JSONL.
5. Chạy `PYTHONPATH=tests:. python3 -m unittest discover -s tests` và ghi kết quả vào commit.

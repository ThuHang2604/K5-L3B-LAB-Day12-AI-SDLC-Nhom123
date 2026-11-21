# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm

> Cập nhật file này qua các phase (lịch sử git phải cho thấy điều đó). Ngắn gọn, có lệnh chạy thật.

## Lệnh
- Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Headless: `python3 -m chonoi.headless --mode gather|quan|day --seed 1 --ticks 600 --out out.jsonl [--days 1..5]`
- Chơi trên trình duyệt: `python3 -m chonoi.live` (vòng 5 Ngày; `--mode gather|quan` để chơi riêng; WASD, E, Space, Esc/P, Shop 1/2/Enter)
- Chụp màn UI + FPS (cần playwright + Chrome): `python3 tools/ui_shots.py "$PWD" docs/proof/phase-2/ui`
- Bằng chứng + smoke hai tiến trình: `bash tools/proof.sh <phase>` → `docs/proof/phase-<n>/`
- Benchmark: `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json` · Soak: `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json`
- Đóng gói: `bash tools/package.sh v1.0.0`

## Cấu trúc & quy ước
- (Starter Python là TÙY CHỌN; nhóm có thể dùng ngôn ngữ khác nếu giữ Test Contract.) Khung do giảng viên cấp: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/`. Hạn chế sửa; nếu phải sửa thì báo cả nhóm và ghi lại lý do.
- Luật chơi của nhóm: `chonoi/sim/gather.py`, `chonoi/sim/quan.py`, `chonoi/sim/day.py`. Thứ tự một bước ghi ở docstring đầu mỗi file — sửa luật thì sửa docstring cùng lúc.
- Trạng thái chỉ dành cho UI (màn chuyển, thống kê) nằm ở `chonoi/live.py`, khóa riêng (`ui_hold`, `stats`), không được trùng khóa snapshot.
- **Số liệu chỉ đọc từ `game.contract.json` / dữ liệu**, không hard-code trong luật.
- Độ tươi chỉ tính bằng đơn vị nguyên qua `chonoi/fresh.py` (240/điểm); không so ngưỡng bằng số thực.
- Mọi số ngẫu nhiên đi qua `Streams` (`chonoi/rng.py`); không dùng `random` toàn cục, không dùng đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` (khóa contract) hoặc schema kho khi chưa báo cả nhóm (đổi hợp đồng ảnh hưởng mọi module).
- Không làm hỏng nhánh chính: trước khi đẩy, chạy test.
- Không bịa yêu cầu: chỗ mơ hồ thì ghi `docs/clarify.md` và hỏi PO.
- Không sửa test cho xanh khi luật sai; phải sửa luật hoặc ghi lý do đổi test trong commit.

## Quy tắc làm việc với agent
- Mỗi agent một việc rõ ràng (một lát). Cho agent đọc PRD/ticket đúng phase và hợp đồng kho trước.
- Agent làm xong phải chạy test và ghi kết quả vào mô tả commit hoặc `docs/proof/`; người đọc lại thay đổi trước khi đẩy.
- Sáng tạo thêm được khuyến khích nhưng phải tắt ở headless (xem README, mục "Tự do sáng tạo").

## Skills / hooks của nhóm
- `.agents/skills/run-smoke/` — chạy test + smoke gather→quan, lưu bằng chứng; dùng trước khi gắn tag.
- `.agents/skills/contract-check/` — checklist đối chiếu thay đổi luật với Test Contract; dùng trước mỗi commit sửa `chonoi/sim/*`.

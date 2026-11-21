# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: chốt giao diện chuyển pha (tham số của GatherSim/QuanSim) trước nên DaySim ghép hai buổi cũ không phải sửa luật; test hộp đen viết theo AC bắt được 2 lỗi lệch tick.
- Điều tệ: tên khóa trùng giữa snapshot và trạng thái UI (`hold`) chỉ lộ ra khi chạy trình duyệt thật; một lát (UI) xong muộn hơn các lát luật nên tích hợp dồn cuối phase.
- 1 hành động cho Phase 3: chạy `tools/ui_shots.py` trong `tools/proof.sh` mỗi lần đổi UI (người nhận: QA lead).

## Phase 3 (nhanh — đổi kho)
- Rút ra: chốt schema + ADR và migrate test **trước** khi chia lát giúp ba lát (gather/quán/HUD) chạy song song mà main không đỏ lâu. Helper `items(...)` trong `tests/helpers.py` làm migrate fixture nhanh.
- Vướng: số thực ở ngưỡng 30 — giải bằng đơn vị nguyên.

## Phase 4 (cuối)
- **Rà hành động P2** ("chạy chụp màn hình UI mỗi lần đổi UI", người nhận: QA lead): đã làm một phần — P3 và P4 đều chụp lại (`docs/proof/phase-3/ui`, `docs/proof/phase-4/ui`) nhưng vẫn chạy tay vì Playwright không có sẵn trên mọi máy nên chưa gắn vào `tools/proof.sh`. Hành động tiếp: thêm bước tùy chọn "nếu có Playwright thì chụp" vào proof.sh (Dung).
- **Điều tốt:** chia file theo người mỗi phase nên gần như không xung đột; ADR + migrate test trước khi chia lát ở P3; test hộp đen theo AC bắt được nhiều lỗi lệch tick.
- **Điều cần sửa:** TEAM.md điền handle muộn; một số commit gộp nhiều việc; nên bật CI trên GitHub để thấy đỏ/xanh ngay khi push.
- **Số liệu:** số commit theo người xem `git shortlog -sn --all`; mỗi người đọc lát kế bên trước khi gộp; token AI không đo được trong giao diện chat (xem `docs/ai-usage-log.md`).
- **Một lần AI sai và cách nhóm xác minh:** P2 AI dùng trùng khóa `hold` cho trạng thái UI và giỏ trong `/state` → client vỡ HUD; phát hiện bằng chụp màn hình Chrome headless, sửa thành `ui_hold` và thêm test `test_live.LiveDayFlow` kiểm `hold` vẫn là mảng.
- **Nếu làm lại:** bật CI + ruleset từ đầu; chốt đơn vị độ tươi/uy tín bằng số nguyên ngay từ P1 thay vì đợi ticket đổi.

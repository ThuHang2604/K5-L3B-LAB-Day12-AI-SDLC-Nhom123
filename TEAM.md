# TEAM

**Tên nhóm:** Nhom123 (`team: "nhom123"`)  **Số người:** 4  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Đỗ Thị Thu Hằng | [ThuHang2604](https://github.com/ThuHang2604) | `sim/day` (vòng ngày, Shop), adapter kho cá thể, `soak`, `tests/` | PO, QA lead (trưởng nhóm, chủ fork) | `sim/quan` |
| Nguyễn Khánh Linh | [xrkhanhlinh](https://github.com/xrkhanhlinh) | `sim/gather` (lặn, cá, Cá Sấu, độ tươi giỏ) | Integrator (giữ `docs/contracts/`, gắn tag, Release) | `sim/day` |
| Trần Thành Vinh | [vinhs0](https://github.com/vinhs0) | `sim/quan` (khách, giữ chỗ, bếp, tiền, giá theo tươi) | Scrum/Release, Đóng gói | `sim/gather` |
| Đặng Thùy Dung | [dtdung14](https://github.com/dtdung14) | `client/ui` (`chonoi/web`, `chonoi/live.py`, HUD, `bench`) | QA UI, Bench | `sim/quan` |

**Vai quy trình:** PO (đầu mối hỏi Anh Năm/giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag `phase-n`, công bố Release) · QA lead (giữ test + ma trận truy vết) · Scrum/Release (theo dõi mốc, đóng gói).

## Thỏa thuận làm việc nhóm

- Kênh liên lạc: nhóm chat của lớp; việc vướng ghi lên kênh kèm link commit/file.
- Khi bất đồng về thiết kế: mỗi bên nói 2 phút; chưa xong thì Integrator (Linh) quyết và ghi lý do vào `docs/clarify.md`.
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trên kênh, người dự phòng (cột cuối) nhảy vào pair.
- Giờ standup: phút 20 và phút 35 của mỗi phase, 2–3 phút (đã xong / sắp làm / vướng), ghi `docs/standup.md`.
- Đọc code của nhau: mỗi người đọc lát kế bên trước khi gộp; đổi hợp đồng (`docs/contracts/`) cần 2 người xem.
- Git: `git pull --rebase` trước khi làm; push thẳng `main` sau khi `PYTHONPATH=tests:. python3 -m unittest discover -s tests` xanh; mỗi phase chỉ một người sửa một file (theo bảng trong kế hoạch phase); Linh gắn tag `phase-n` sau khi Hằng chạy `bash tools/proof.sh n`.

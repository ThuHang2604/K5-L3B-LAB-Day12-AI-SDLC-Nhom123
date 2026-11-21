# Tích hợp phần Linh — 2026-11-21

Nhánh làm việc: `linh`. Tài khoản Git: `xrkhanhlinh`.

## Nguồn và phạm vi

- Đọc `HUONG_DAN_Linh.md`, `plan.json`, `apply.py` trong bộ `HuongDan-Nhom123/HuongDan-Nhom123` cạnh repo.
- Bắt đầu từ `origin/main` tại `4817dcd`, đã có các phần của Hằng và Dung. Gộp `origin/TranThanhVinh` tại `4035a48` bằng commit `69e139a` để tích hợp CLI, quán và đóng gói; giữ nguyên lịch sử và tác giả của Vinh.
- Áp phần Linh từ `snapshots/phase-4` cho trạng thái tích hợp cuối: `chonoi/sim/gather.py`, skill `contract-check`, hợp đồng kho, mẫu/schema và release notes. Không chạy tuần tự các bước sao chép snapshot cũ vì sẽ hạ các module dùng chung đang ở v1.3.
- Manifest v1.3, `chonoi/contract.py`, `chonoi/__init__.py`, `chonoi/scenario.py`, `tests/test_rules_p1.py` và `CHANGELOG.md` đã khớp snapshot cuối nên giữ nguyên.
- Sau tích hợp, toàn bộ file trong `chonoi/` và `tests/` khớp snapshot phase-4 khi chuẩn hóa LF/CRLF. Không thay test để né lỗi luật.

## Đối chiếu contract

- `GatherSim.step()` ghi rõ thứ tự xử lý trong docstring: hao tươi hàng cũ; bơi/oxy/ngạt/ngất; quái và tối đa một hit; cập bến trước hái; bắt cá; hết giờ; cá bơi/sinh nếu còn giờ.
- Giá trị gameplay đọc từ tuning; độ tươi qua `chonoi/fresh.py` dùng đơn vị nguyên; RNG qua `Streams`; cấp và sắp id qua bộ công cụ id.
- Kiểm tra schema scenario/inputs đã có trong các module dùng chung. Test đầu vào sai trả mã 2 và test tính tất định đều nằm trong bộ regression.
- Bộ hướng dẫn không kèm PRD/ticket gốc. Đối chiếu dựa trên snapshot được cung cấp, manifest, ADR, tài liệu hợp đồng và bộ test hiện có; không tuyên bố đã đọc PRD/ticket ngoài repo.

## Kiểm chứng

- [Test tích hợp lần đầu](tests.txt): **92 test, OK, RESULT: PASS**.
- Chạy skill `run-smoke` bằng `bash tools/proof.sh 4`; bằng chứng ở [phase-4](../phase-4/).
- [Test regression](../phase-4/tests.txt), [bàn giao gather → quán](../phase-4/integration-check.txt), [tất định](../phase-4/determinism.txt), [ngưỡng độ tươi](../phase-4/threshold-check.txt), [nâng cấp xuyên Ngày](../phase-4/days-upgrades.txt).
- [Soak](../phase-4/soak.json): **10/10 Ngày, 0 crash**.
- [Benchmark](../phase-4/bench.json) và [renderer](../phase-4/bench-stderr.txt): máy thiếu Playwright, sử dụng renderer software theo cơ chế dự phòng; FPS không đại diện cho trình duyệt.
- [Clone sạch](../phase-4/clean-clone.txt): kiểm máy chủ `/state` và chạy lại test trên commit đã ghi trong [env.txt](../phase-4/env.txt).
- Ảnh UI trong `phase-4/ui/` là bằng chứng có sẵn của Dung, không phải ảnh chụp lại trong lần tích hợp này.

Trên Windows dùng Python 3.11.9 và Git Bash. Đã tạo môi trường Python tạm ngoài repo có launcher `python3.exe` để các lệnh trong manifest chạy được, không thay manifest hay test vì khác nền tảng.

## Các bước còn phụ thuộc nhóm

- P4-07: Linh cần tự viết phản tư cá nhân ≤ 200 từ theo `docs/members/TEMPLATE.md`. Bản trong bộ hướng dẫn còn placeholder; chưa đưa vào repo như một bài phản tư đã hoàn thành.
- Gắn tag phase và công bố Release yêu cầu trạng thái trên `main` đã được nhóm tích hợp và kiểm chứng. Lần này chuẩn bị và push nhánh `linh`; chưa gắn tag lịch sử hoặc công bố Release từ nhánh cá nhân.
- Khi bàn giao, nhóm cần đọc lại thay đổi hợp đồng theo thỏa thuận trong `TEAM.md`.

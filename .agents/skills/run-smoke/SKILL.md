---
name: run-smoke
description: Chạy toàn bộ test + smoke hai tiến trình (gather -> quan) và lưu bằng chứng vào docs/proof/phase-<n>/. Dùng trước khi gắn tag hoặc sau mỗi lần tích hợp lát.
---

1. `bash tools/proof.sh <n>` (n = số phase đang làm).
2. Đọc dòng cuối `docs/proof/phase-<n>/tests.txt` phải là `RESULT: PASS`; `integration-check.txt` phải `ĐẠT`.
3. Nếu chưa đạt: KHÔNG sửa test cho xanh; tìm luật sai trong `chonoi/sim/*`, ghi lý do vào commit.
4. Cập nhật bảng AC trong `docs/verification/phase-<n>.md` bằng đường dẫn tới file bằng chứng.

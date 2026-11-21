# ADR 0001 — Đổi kho đếm sang kho cá thể (Test Contract v1.2)

- Trạng thái: Chấp nhận (Phase 3, TICKET-03 "Mùa Nước Nổi")
- Bối cảnh: khách hàng cần theo dõi độ tươi từng nguyên liệu từ lúc vào giỏ tới lúc vào bếp. Kho `{"items":{kind:n}}` không mang được id/độ tươi.
- Quyết định:
  1. Schema mới `{"items":[{"id","kind","fresh"}]}`; v1.2 trả mã 2 cho kho đếm. Không giữ chế độ đọc hai phiên bản ở runtime vì manifest chỉ có một `contract_version` (hàm đọc kho đếm cũ giữ lại trong `inventory.py` chỉ để tham khảo).
  2. Độ tươi tính bằng số nguyên **240 đơn vị/điểm** (`chonoi/fresh.py`): gather −2/tick, quán −1/tick; so ngưỡng 30 (= 7200) và `floor` giá bằng `Fraction` → không lệch nhánh do số thực.
  3. File kho ghi `fresh` đủ độ chính xác (không làm tròn 3 chữ số như JSONL); bên đọc đổi về đơn vị và làm tròn nếu sai số < 1e-6.
  4. Id cá thể dùng chung `IdAllocator` của lượt (`I1, I2, …`), nên tăng xuyên pha và Ngày.
- Thứ tự tích hợp để `main` luôn chạy: (a) `fresh.py` + `inventory.py` + manifest v1.2 + migrate test → (b) gather → (c) quán → (d) day → (e) HUD → (f) proof/docs. Mỗi bước chạy đủ test trước khi đẩy.
- Hệ quả: fixture cũ phải viết lại (`hold`/`stock` là mảng cá thể, `reserved` là mảng id). Cách cập nhật ghi ở `CHANGELOG.md`.

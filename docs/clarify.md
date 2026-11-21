# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

Cột "Trả lời / giả định": mọi dòng dưới đây hiện là **giả định của nhóm**, chưa có xác nhận từ giảng viên.
PO cần hỏi và cập nhật; nếu câu trả lời khác thì sửa luật + test, ghi lý do trong commit.

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 21/11/2026 | Ngạt: tick oxy chạm 0 có tính vào `zero_oxy_ticks` ngay tick đó không? | Có: oxy giảm rồi xét ngạt trong cùng bước, nên choke đến sau đúng `choke_interval_ticks` tick kể từ `oxygen_empty` (tính cả tick đó). | Nhóm 123 |
| 2 | 21/11/2026 | Giỏ gần đầy: hái/bắt đàn cá cho nhiều món hơn chỗ trống thì sao? | Tất cả hoặc không: không đủ chỗ cho cả `node_yield` / `fish_yield[kind]` thì phát `hold_full`, không đổi nút/cá. | Nhóm 123 |
| 3 | 21/11/2026 | `catch` hụt (không có đàn cá trong `catch_radius`) có tốn hồi chiêu không? | Không. Hồi chiêu chỉ bắt đầu sau lần bắt trúng. | Nhóm 123 |
| 4 | 21/11/2026 | Nút mọc lại tính từ lúc nào? | Từ tick hái: `regrow_s` giây sau tick `gather`. | Nhóm 123 |
| 5 | 21/11/2026 | Khách chọn món thế nào khi nhiều món nấu được? | Chọn ngẫu nhiên đều qua luồng `Streams.get("customer_dish")` trong danh sách món sắp theo id (cùng seed → cùng kết quả). | Nhóm 123 |
| 6 | 21/11/2026 | Khách đến nhưng không còn bàn trống? | Khách không vào quán, không sự kiện, không trừ uy tín. | Nhóm 123 |
| 7 | 21/11/2026 | `no_dish`: khách đến nhưng không món nào nấu được? | Phát `no_dish`, khách không ngồi, không trừ uy tín (khác `customer_left`). | Nhóm 123 |
| 8 | 21/11/2026 | `interact` quán chọn đối tượng nào? | Gần nhất trong `interact_radius` theo (khoảng cách, bếp trước bàn, id), rồi mới xét có làm được gì không; tối đa một đối tượng mỗi tick. | Nhóm 123 |
| 9 | 21/11/2026 | Bếp nấu món của khách nào? | Khách `assigned` chưa nấu có id nhỏ nhất. Nguyên liệu trừ khỏi kho lúc `cook_started` (giữ chỗ chuyển thành đã dùng). | Nhóm 123 |
| 10 | 21/11/2026 | Boa: điều kiện và số tiền? | Nếu kiên nhẫn còn lại lúc phục vụ ≥ `tip_min_patience_ratio` × `patience_s`: boa = round(giá × `tip_rate`) và uy tín +`tip_reputation`. Tiền tính khi `paid`. | Nhóm 123 |
| 11 | 21/11/2026 | Kiên nhẫn giảm lúc nào? | Mỗi tick khi khách chờ món (`assigned`); dừng khi đã được phục vụ (`eating`). Hết → `customer_left`, uy tín +`left_reputation_delta`, kẹp [min, max]. | Nhóm 123 |

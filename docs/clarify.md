# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Phase | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | P1 | `base_price`/`tip` của khách trước khi chốt giá/phục vụ ghi gì trong snapshot? | Giả định `null` tới khi chốt (bắt đầu nấu → `base_price`, phục vụ → `tip`). | Nhóm |
| 2 | P1 | Bếp idle mà không còn đơn `reserved` thì E làm gì? | Bỏ lượt, không sự kiện (đúng "đối tượng không tương tác được"). | Nhóm |
| 3 | P1 | `items` của `cook_started` có lặp kind theo số lượng không? | Có: mảng kind theo số lượng, sắp theo kind (vd `["ca_linh","ca_linh","ca_linh","bong_dien_dien"]` sau khi sắp). | Nhóm |
| 4 | P1 | Khách hết kiên nhẫn khi món đang nấu/trên tay? | Bỏ món đó (bếp về idle / tay trống), nguyên liệu đã dùng không hoàn. | Theo PRD F |
| 5 | P1 | `dive`/`surface` khi bắt đầu đúng biên d = 0.5? | So `d ≤ surface_depth` đầu và cuối bước; chỉ phát khi đổi phía. | Theo PRD F |
| 6 | P2 | Hướng cá mới/đổi hướng "theo seed" phân bố thế nào? | Giả định đều trên [0°, 360°) qua luồng RNG riêng (`fish_init`, `fish_turn`, `fish_spawn`). | Nhóm |
| 7 | P2 | 8 đàn đầu ca chọn thế nào? | Lặp thủ tục sinh 8 lần (trọng số loài, điểm đều, cách > 1 m) → 8 điểm hình học khác nhau. | Nhóm |
| 8 | P2 | Cá Sấu xét phát hiện trước hay sau khi di chuyển? | Xét chuyển trạng thái theo vị trí đầu bước của quái và vị trí người chơi sau bơi, rồi di chuyển; chạm xét sau khi cả hai di chuyển. | Nhóm |
| 9 | P2 | Ngưỡng "người chơi ở d ≥ 10" của quái lấy từ đâu? | `species.depths[0]` (Cá Sấu 10) để mở rộng Rắn dùng 8. | Nhóm |
| 10 | P2 | Khối `gather.hold` trong scenario day áp cho Ngày nào? | Mẫu khởi tạo mỗi Ngày (theo 4.3 "làm mẫu khởi tạo mỗi Ngày"). | Theo ticket |
| 11 | P2 | `day.upgrades` trong scenario là cấp đã mua hay đang áp dụng? | Cả hai ở Ngày đầu (lượt bắt đầu với các cấp đó). | Nhóm |
| 12 | P2 | Lệnh Shop của mở rộng chưa bật (`weapon`, `buy:ca_loc`…)? | `buy_failed` với `reason: unknown` (lệnh không hỗ trợ). Nút `attack`/`photo` chưa bật → trường lạ, mã 2. | Nhóm |
| 13 | P3 | Độ tươi biểu diễn thế nào để chính xác ở ngưỡng 30? | 240 đơn vị/điểm (gợi ý trong ticket): gather −2, quán −1 đơn vị/tick; giá dùng `Fraction`. | Nhóm (ADR 0001) |
| 14 | P3 | `customers[].reserved` trong snapshot sắp thế nào? | Sắp theo id (tiền tố, hậu tố số). | Nhóm |
| 15 | P3 | Hàng thô trong `stock` của Shop có hao không? | Không (theo ticket); Shop xuất mảng cá thể dư từ ca, bị bỏ khi dựng Ngày mới. | Theo ticket |
| 16 | P3 | Đơn chuyển `unfulfillable` có thử giữ lại ở bước sau không? | Không; chỉ thử đúng một lần khi phần giữ vừa ươn, khách chờ tới hết kiên nhẫn. | Theo ticket |
| 17 | P4 | `load_ms` tính từ đâu? | Từ lúc tiến trình `bench_cmd` khởi chạy (Linux đọc `/proc/self/stat`) tới khung hình đầu tiên của cảnh lặn có snapshot. | Nhóm |
| 18 | P4 | Máy chấm không có trình duyệt thì bench làm sao? | `--renderer auto`: thử Playwright + Chrome/Chromium, thiếu thì dùng rasterizer Python 1280×720 vẽ cùng cảnh; ghi renderer ra stderr, bench.json vẫn đúng 5 trường. | Nhóm |
| 19 | P4 | Soak dùng input gì? | Bot tất định trong `chonoi/soak.py` đọc trạng thái sim (hái bông → về bến; nấu/bưng/phục vụ; Shop mua nâng cấp rồi đóng). Kế hoạch D1–D5 lặp ở Ngày 6–10. | Nhóm |

# dungdt14 — phản tư cá nhân (Đặng Thùy Dung, QA UI + Bench)

- **Phần tôi làm:** P1 adapter đọc kho theo contract (`add7f8b`); P2 menu, các màn chuyển, pause, HUD, `test_live.py`, `ui_shots.py` (`fd3a285`); P3 HUD độ tươi (`fa2c165`); P4 `bench.py` 1280×720, cảnh báo chữ + biểu tượng, tương phản cao (`0468a4a`).
- **Đã giúp ai:** chụp ảnh UI cho Hằng gắn ma trận truy vết; báo Linh cá đứng yên ở mép; báo Vinh kiên nhẫn hiển thị âm sau khi khách rời bàn.
- **AI sai ở đâu và tôi phát hiện thế nào:** AI đặt trạng thái màn chuyển vào khóa `hold`, trùng giỏ của snapshot → HUD giỏ trống dù vừa hái. Tôi thấy qua ảnh chụp Chrome headless, đổi sang `ui_hold`. Công cụ chép file còn suýt ghi đè `inventory.py` v1.2 bằng v1.0; tôi so với snapshot trước khi commit nên bỏ qua.
- **Bài học:** UI chỉ đọc snapshot, giữ trạng thái riêng ở khóa khác; kiểm bằng ảnh chụp thật, không chỉ tin test.

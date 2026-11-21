# xrkhanhlinh — phản tư cá nhân (Linh, gather + Integrator)

- **Phần tôi làm:** Tôi dùng AI hỗ trợ tích hợp phần lặn, oxy, cá, Cá Sấu và độ tươi giỏ từ bản nguồn của nhóm ([commit](https://github.com/ThuHang2604/K5-L3B-LAB-Day12-AI-SDLC-Nhom123/commit/f45fcb6)). Tôi cũng bổ sung hợp đồng kho, schema và release notes.
- **Hỗ trợ nhóm:** Tôi gộp phần quán của Vinh vào nhánh tích hợp, giữ nguyên tác giả ([commit](https://github.com/ThuHang2604/K5-L3B-LAB-Day12-AI-SDLC-Nhom123/commit/69e139a)). Phần bàn giao được kiểm tra bằng smoke gather → quán; 92 test đạt, soak đủ 10 Ngày và không crash.
- **AI sai ở đâu:** Ban đầu AI báo chưa tìm thấy mã nguồn vì kiểm tra thiếu một cấp thư mục `HuongDan-Nhom123`. Sau khi kiểm lại đường dẫn, bản nguồn đã được tìm thấy. Việc này nhắc tôi phải kiểm chứng kết luận của AI bằng file thực tế.
- **Bài học:** Tích hợp cần hiểu phiên bản dữ liệu và phần việc của từng người. Tôi thấy giữ nguyên thay đổi đã đúng, chạy thử và lưu bằng chứng giúp cả nhóm dễ kiểm tra hơn.

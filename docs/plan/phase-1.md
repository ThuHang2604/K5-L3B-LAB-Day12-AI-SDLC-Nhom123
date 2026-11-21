# Kế hoạch Phase 1

- Mục tiêu: hai buổi chơi được, nối qua file kho, đúng Test Contract v1.0; tag `phase-1` trước 1:00.
- Hợp đồng chốt trước khi tách lát: [`docs/contracts/README.md`](../contracts/README.md) (schema kho + sự kiện + sim↔UI). Lát 3–4 dùng `docs/contracts/inventory.sample.json` làm kho mẫu khi lát 2 chưa xong.

| Việc | AC | Người | Phụ thuộc |
|---|---|---|---|
| Lát 1: bơi, oxy, ngạt, ngất, chặn biên, giỏ | AC-P1-01..03 | Linh | — |
| Lát 2: hái, bắt cá, cập bến, ghi kho | AC-P1-04..06 | Linh (pair Dung: kho đọc theo contract) | lát 1 (giỏ) |
| Lát 3: khách, giữ chỗ, kiên nhẫn, no_dish | AC-P1-07..08 | Vinh | hợp đồng kho |
| Lát 4: bếp, bưng, phục vụ, tiền, boa, uy tín, đóng ca | AC-P1-09..11 | Vinh | lát 3 (đơn) |
| HUD / QA / ma trận truy vết | AC-P1-12..14 | Dung (HUD), Hằng (QA, ma trận) | tất cả |

- Rủi ro: thứ tự bước (ngạt t+59, hồi chiêu t+L) dễ lệch một tick → viết test biên trước; fixture quán mâu thuẫn phải trả mã 2 trước khi ghi JSONL.

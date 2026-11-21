---
name: proof-run
description: Dùng khi agent hoặc người xong một lát/phase: chạy toàn bộ test, kiểm tất định theo seed, và ghi bằng chứng thật vào docs/proof/phase-n/.
---

# proof-run

Khi nào dùng: cuối mỗi lát, và ngay trước khi gắn tag `phase-n`.

1. Chạy `python3 .agents/skills/proof-run/run.py <n>` (n = số phase).
2. Script ghi `docs/proof/phase-<n>/test-output.txt` và `determinism.txt` từ lần chạy THẬT. Không sửa tay hai file này.
3. Nếu có test đỏ: sửa luật (hoặc ghi lý do đổi test trong commit). Không xóa test cho xanh.
4. Dán đường dẫn hai file vào ma trận `docs/verification/phase-<n>.md` rồi commit cùng thay đổi.

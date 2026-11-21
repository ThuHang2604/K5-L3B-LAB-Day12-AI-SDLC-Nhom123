# Hợp đồng tích hợp (chốt ở kickoff Phase 1, cập nhật P2 — v1.1, P3 — v1.2 kho cá thể)

## 1. File kho gather → quan (v1.2 — kho cá thể, xem [ADR 0001](../adr/0001-kho-ca-the-v1-2.md))

```json
{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 97.5}]}
```

- Gốc chỉ có khóa `items`: **mảng** cá thể `{id, kind, fresh}`. Kho rỗng: `{"items":[]}`. `id` chuỗi khác rỗng, duy nhất; `kind` thuộc 6 nguyên liệu; `fresh` hữu hạn trong [0, 100].
- Bên đọc: contract v1.2 trả mã 2 cho kho đếm (object), sai schema, kind lạ, id trùng, fresh ngoài miền. Quán nhận nguyên id, độ tươi, kể cả hàng ươn. Trần giỏ không áp lên kho quán.
- Bên ghi (`gather --inventory-out`): đúng một lần khi có `gather_end` (ngất → `{"items":[]}`), sắp theo id, `fresh` đủ chính xác (không làm tròn) để giữ nhánh ở ngưỡng 30; file tạm cùng thư mục rồi `os.replace`. Chạm `--ticks` trước `gather_end`: không đụng file đích.
- `--mode day` bàn giao trong bộ nhớ cùng schema, cùng tick đổi pha, không hao thêm.
- Id `I1, I2, …` cấp theo thứ tự vào giỏ, tăng xuyên pha và Ngày.
- File mẫu: [`inventory.sample.json`](inventory.sample.json). Schema: [`inventory.schema.json`](inventory.schema.json).

## 2. Giao diện sim ↔ UI

- Màn chuyển (menu, DayIntro, EveningIntro, DayResult, Summary) chỉ là UI: server giữ sim (`ui_hold` trong `/state`) tới khi UI gọi `POST /continue`; headless không có bước này.
- UI (`chonoi/web/index.html`) **chỉ đọc** snapshot (cùng trường với dòng snapshot headless) qua `GET /state`, cộng `events` gần nhất và `meta` (tuning).
- UI **gửi vào** trạng thái phím đang giữ: `POST /input {"move":[a,b], "interact", "catch", "pause", "shop_done": bool, "buy": "oxygen"|"hp"}`. Cạnh lên do sim tính (`LiveInputs`).

## 3. Sự kiện

| Pha | Sự kiện (ai phát: sim) | Ai nghe |
|---|---|---|
| gather | `gather`, `node_regrown`, `hold_full`, `fish_caught`, `fish_spawned`, `dive`, `surface`, `oxygen_empty`, `choke`, `monster_hit`, `faint`, `gather_end` | UI, file kho / day |
| quan | `customer_arrived`, `no_dish`, `cook_started`, `dish_ready`, `dish_picked`, `served`, `paid`, `customer_left`, `quan_end` | UI, DayResult |
| mọi mode | `paused`, `resumed` | UI |
| gather, quan | `spoiled {item_id, kind, location}` (v1.2) | UI (HUD độ tươi) |
| day/shop | `day_start`, `day_plan`, `phase_start`, `bought`, `buy_failed`, `shop_end` | UI (DayIntro, Shop) |

`data` của từng sự kiện theo Test Contract mục E (v1.0) và 4.4 (v1.1). Trong `day`, vỏ event có thêm `day`; event kết thúc mang pha cũ; snapshot đổi pha ghi pha mới với `phase_tick: 0`.

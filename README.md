# Quán Ăn Chợ Nổi — Nhom123 (Day 12 · AI SDLC) · v1.0.0

Út Sen lặn bắt cá, hái bông trên sông Chín Khúc buổi sáng (`gather`), tối mở quán trên nhà bè của Má Tư (`quan`), cuối ngày mua nâng cấp ở Shop. Lab board: [Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg). Đề gốc: [`docs/STARTER.md`](docs/STARTER.md). Bản phát hành: [`docs/release/v1.0.0.md`](docs/release/v1.0.0.md).

## Yêu cầu môi trường

- macOS hoặc Linux, **Python ≥ 3.10** (chỉ thư viện chuẩn), một trình duyệt hiện đại (Chrome, Firefox, Safari).
- Tùy chọn: Playwright + Chrome/Chromium, chỉ cho benchmark có render bằng trình duyệt và chụp màn hình bằng chứng.

## Chạy từ clone sạch (3 lệnh)

```bash
git clone https://github.com/<owner>/K5-L3B-LAB-Day12-AI-SDLC-Nhom123.git
cd K5-L3B-LAB-Day12-AI-SDLC-Nhom123
python3 -m chonoi.live          # mở http://127.0.0.1:8000/ — vòng 5 Ngày (thêm --days N, --seed N, --port N)
```

Chơi riêng từng buổi: `python3 -m chonoi.live --mode gather --inventory-out kho.json` rồi `python3 -m chonoi.live --mode quan --inventory kho.json`.

## Lệnh test, headless, benchmark, soak

| Việc | Lệnh |
|---|---|
| Test (1 lệnh) | `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` |
| Headless (Test Contract v1.3, gameplay v1.2) | `python3 -m chonoi.headless --mode gather\|quan\|day --seed <int> --ticks <N> --out out.jsonl [--days 1..5] [--scenario f] [--inputs f] [--inventory f] [--inventory-out f] [--snapshot-every N]` |
| Benchmark có render | `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json` (`--renderer browser\|software`, mặc định `auto`) |
| Soak 10 Ngày | `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json` |
| Bằng chứng một phase | `bash tools/proof.sh <n>` → `docs/proof/phase-<n>/` |
| Đóng gói bản phát hành | `bash tools/package.sh v1.0.0` → `dist/quan-an-cho-noi-v1.0.0.zip` |

## Điều khiển

| Phím | Buổi sáng (gather) | Buổi tối (quan) |
|---|---|---|
| WASD / mũi tên | bơi (S/↓ lặn xuống) | đi |
| E | cập bến (trong bến) / hái bông (ở mặt nước) | nấu ở bếp trống / bưng món chín / phục vụ ở bàn |
| Space | bắt đàn cá gần nhất (dưới nước) | — |
| Esc / P | tạm dừng (Tiếp tục / Về menu / Tương phản cao) | tạm dừng |
| H | bật/tắt **tương phản cao** (nhớ giữa các lần mở) | như sáng |
| Shop | `1` mua Bình oxy, `2` mua Áo phao, `Enter` xong sang Ngày kế | |
| R | chơi lại (chỉ khi chơi riêng một buổi) | |

## Luật & cách tính điểm

- **Vòng ngày:** Menu → DayIntro (Má Tư đọc món + nguyên liệu cần lấy) → Lặn & Hái → EveningIntro → Mở Quán → DayResult → Shop → Ngày kế; sau Ngày 5 là Tổng kết. Tiền, uy tín, cấp nâng cấp giữ qua Ngày; oxy/Máu hồi đầy; kho dư bỏ sau Shop.
- **Sáng 180 s:** oxy 30 s, dưới nước −1/tick, mặt nước (d ≤ 0.5) +6/tick; oxy 0 dưới nước → mỗi 60 tick mất 1 Máu (3 Máu). Giỏ 12 ô. 8 đàn cá bơi 1.5 m/s (cá linh nông, cá lóc giữa, cá kèo sâu), sinh thêm mỗi 6 s tới 12 đàn. Hái bông điên điển, bông súng, kèo nèo ở mặt nước. **Cá Sấu Năm Chèo** tuần tra vùng sâu, đuổi khi bạn ở d ≥ 10 trong 10 m; chạm làm mất 1 Máu và rơi nửa giỏ (vào sau rơi trước), bất tử 1.5 s. Máu 0 = ngất, mất cả giỏ (quán vẫn mở với kho rỗng). Cập bến hoặc hết giờ thì mang giỏ về.
- **Tối 180 s:** 2 bếp, 4 bàn, 6 món. Khách đến tick 120 rồi mỗi 15 s nếu có bàn trống, chọn món trong kế hoạch Ngày đủ nguyên liệu và giữ chỗ ngay. Nấu → bưng → phục vụ trước khi hết kiên nhẫn 60 s. Ăn 10 s rồi trả tiền.
- **Độ tươi (v1.2):** mỗi nguyên liệu là một cá thể `I1, I2…` tươi 100 lúc bắt/hái; trong giỏ −0.5/s, trong kho quán −0.25/s. Dưới 30 là **ươn**: vẫn chiếm ô nhưng không nấu được. Khách giữ cá thể tươi nhất; giá món = `floor(giá niêm yết × độ tươi trung bình / 100)`.
- **Boa** = `floor(giá đã chốt × 0.2)` nếu lúc phục vụ còn ≥ 50% kiên nhẫn; boa dương +0.2 uy tín. Khách bỏ đi −0.5 uy tín. Uy tín đầu 3.0, kẹp [0, 5].
- **Shop:** Bình oxy 200 → 45 s, 400 → 60 s; Áo phao 250 → 4 Máu, 500 → 5 Máu. Có hiệu lực từ Ngày kế; Shop tự đóng sau 10 s.
- **Điểm = earned + 100 × floor(uy tín)** (earned = tổng tiền món + boa, nghìn đồng).

## Cảnh báo dễ nhận biết

| Cảnh báo | Chữ | Biểu tượng / hình |
|---|---|---|
| Thủy quái gần | "Thủy quái! Lên chỗ cạn (d < 10)" | tam giác "!" + viền tím quanh màn hình, Cá Sấu viền hồng ở tương phản cao |
| Oxy sắp hết (< 25%) | "Sắp hết oxy! Còn n s" / "Hết hơi!" | tam giác "!", thanh oxy đỏ nhấp nháy |
| Khách sắp giận (kiên nhẫn < 25%) | "Khách bàn Tn sắp giận — phục vụ ngay!" + "Sắp giận!" dưới bàn | tam giác "!" cạnh khách, thanh kiên nhẫn đỏ |

Tương phản cao: nền HUD đen đặc viền trắng, cảnh báo nền đen viền vàng chữ trắng đậm, cảnh tăng tương phản/bão hòa, Út Sen viền trắng. Ảnh: [`docs/proof/phase-4/ui/`](docs/proof/phase-4/ui/).

## Hợp đồng file kho

`{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}]}` (kho cá thể v1.2). Chi tiết schema, sự kiện và giao diện sim ↔ UI: [`docs/contracts/README.md`](docs/contracts/README.md), quyết định đổi schema: [ADR 0001](docs/adr/0001-kho-ca-the-v1-2.md).

## Cấu trúc

- `chonoi/sim/gather.py` (lặn, cá, Cá Sấu, độ tươi giỏ), `chonoi/sim/quan.py` (quán, giữ chỗ theo id, giá theo tươi), `chonoi/sim/day.py` (vòng ngày + Shop), `chonoi/fresh.py` (độ tươi 240 đơn vị/điểm): luật, chỉ đọc số từ `game.contract.json`.
- `chonoi/{headless,runner,inputs,scenario,inventory,...}.py`: CLI, tick, JSONL tất định. `chonoi/bench.py`, `chonoi/soak.py`: lệnh Phase 4.
- `chonoi/live.py` + `chonoi/web/index.html`: giao diện trên trình duyệt dùng cùng lớp sim.
- `tests/`: smoke hộp đen + `test_rules_p1..p3.py`, `test_release_p4.py` (regression P1–P3 chạy với luật hiện hành).

## Mở rộng

Nhóm 4 người: không bắt buộc, không bật mở rộng nào (`"extensions": []`). Nút `attack`/`photo` bị từ chối (mã 2), lệnh Shop ngoài `oxygen`/`hp` → `buy_failed unknown`.

## Sáng tạo của nhóm

Chỉ ở lớp giao diện (`chonoi/web/index.html`), không đụng tick, sự kiện, tiền, uy tín hay snapshot:
- Má Tư dặn món bằng giọng Nam Bộ ở DayIntro; tiệm nâng cấp mang tên "Tiệm Chú Ba".
- Cảnh sáng ánh hồng + bờ dừa nước, vạch vùng nông/giữa/sâu; tối có đèn dây vàng nhấp nháy, khói bếp khi đang nấu; Út Sen áo bà ba xanh, khăn rằn đỏ, kính lặn.
- Cá Sấu đổi màu tím khi đuổi, Út Sen nhấp nháy khi bất tử; ô màu độ tươi cạnh giỏ.

Bằng chứng lõi vẫn đúng: toàn bộ test hộp đen ([`docs/proof/phase-4/tests.txt`](docs/proof/phase-4/tests.txt)) và JSONL tất định từng byte ([`determinism.txt`](docs/proof/phase-4/determinism.txt)) chạy qua headless, không nạp file web nào.

## Tài liệu nhóm

[`TEAM.md`](TEAM.md) · [`AGENTS.md`](AGENTS.md) · [`CHANGELOG.md`](CHANGELOG.md) · verification [P1](docs/verification/phase-1.md) · [P2](docs/verification/phase-2.md) · [P3](docs/verification/phase-3.md) · [P4](docs/verification/phase-4.md) · [`docs/clarify.md`](docs/clarify.md) · [`docs/ai-usage-log.md`](docs/ai-usage-log.md) · [`docs/retro.md`](docs/retro.md) · [`docs/plan/`](docs/plan/) · [`docs/members/`](docs/members/) · [LICENSE](LICENSE) · [CREDITS](CREDITS.md)

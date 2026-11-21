"""Benchmark có render (TICKET-04): cảnh buổi sáng lõi 1280×720, Út Sen đứng yên ở bến.

    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json [--warmup 3] [--renderer auto|browser|software]

Cảnh: GatherSim mặc định (độ tươi, 8 đàn cá bơi, Cá Sấu Năm Chèo M1, hiệu ứng mặc định), không input.
Renderer:
  - browser (mặc định khi có): chính client `chonoi/web/index.html` trong Chrome/Chromium headless qua Playwright,
    cửa sổ 1280×720, đo bằng requestAnimationFrame (bỏ giới hạn vsync để thấy trần thật).
  - software (dự phòng khi máy không có Playwright/Chrome): rasterizer Python vẽ cùng cảnh vào framebuffer
    RGB 1280×720 (nền, nút hái, cá, quái, Út Sen, HUD dạng khối). Ghi renderer đã dùng ra stderr.
Xuất đúng năm trường: avg_fps, p1_low_fps, frames, measured_s, load_ms.
"""

import argparse
import json
import math
import os
import shutil
import sys
import time

W, H = 1280, 720


def _process_start_epoch():
    """Thời điểm tiến trình khởi chạy (Linux: /proc), dự phòng: lúc nạp module."""
    try:
        with open("/proc/self/stat") as f:
            start_ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/stat") as f:
            btime = next(int(l.split()[1]) for l in f if l.startswith("btime"))
        return btime + start_ticks / os.sysconf("SC_CLK_TCK")
    except Exception:
        return _IMPORT_TIME


_IMPORT_TIME = time.time()


def metrics(frame_s, measured_s, first_frame_epoch, start_epoch):
    frames = len(frame_s)
    n = max(1, math.ceil(0.01 * frames))
    slow = sorted(frame_s, reverse=True)[:n]
    mean_slow = sum(slow) / len(slow) if slow else 0
    measured_s = round(measured_s, 3)  # avg_fps = frames / measured_s đúng với giá trị đã ghi
    return {"avg_fps": round(frames / measured_s, 2) if measured_s > 0 else 0,
            "p1_low_fps": round(1 / mean_slow, 2) if mean_slow > 0 else 0,
            "frames": frames, "measured_s": round(measured_s, 3),
            "load_ms": max(0, int(round((first_frame_epoch - start_epoch) * 1000)))}


# ------------------------------------------------------------------ browser -----
def _chrome_exe():
    for c in (os.environ.get("CHROME_PATH"), shutil.which("google-chrome"), shutil.which("chromium"),
              shutil.which("chromium-browser"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if c and os.path.exists(c):
            return c
    return None


def run_browser(seed, duration, warmup, tuning):
    from playwright.sync_api import sync_playwright  # noqa: tùy chọn

    from .live import LiveGame, LiveServer
    game = LiveGame("gather", tuning, {}, seed)
    srv = LiveServer(game, port=0)
    srv.start()
    try:
        with sync_playwright() as pw:
            kw = {"args": ["--no-sandbox", "--disable-frame-rate-limit", "--disable-gpu-vsync"]}
            exe = _chrome_exe()
            try:
                browser = pw.chromium.launch(**kw)
            except Exception:
                if not exe:
                    raise
                browser = pw.chromium.launch(executable_path=exe, **kw)
            page = browser.new_page(viewport={"width": W, "height": H})
            page.goto(f"{srv.url}?bench=1&warm={warmup}&dur={duration}")
            deadline = time.time() + warmup + duration + 60
            while game.bench_result is None and time.time() < deadline:
                time.sleep(0.2)
            browser.close()
    finally:
        srv.stop()
    r = game.bench_result
    if not r:
        raise RuntimeError("trình duyệt không gửi kết quả benchmark")
    return [d / 1000.0 for d in r["deltas_ms"]], r["measured_ms"] / 1000.0, r["first_frame_epoch_ms"] / 1000.0


# ------------------------------------------------------------------ software -----
def _rgb(h):
    h = h.lstrip("#")
    return bytes(int(h[i:i + 2], 16) for i in (0, 2, 4))


class SoftRenderer:
    """Rasterizer khối đơn giản cho cảnh lặn: framebuffer RGB 1280×720 trong bytearray."""

    def __init__(self, tuning):
        self.g = tuning["gather"]
        self.fb = bytearray(W * H * 3)
        bg = bytearray(W * H * 3)
        for y in range(H):
            if y < 170:
                c = (247, 190 + y // 8, 170)
            else:
                k = (y - 170) / (H - 170)
                c = (int(185 - 130 * k), int(138 - 100 * k), int(85 - 55 * k))
            bg[y * W * 3:(y + 1) * W * 3] = bytes(c) * W
        self.bg = bytes(bg)
        self.rows = {}

    def _row(self, color, w):
        key = (color, w)
        r = self.rows.get(key)
        if r is None:
            r = self.rows[key] = color * w
        return r

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(W, int(x + w)), min(H, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = self._row(color, x1 - x0)
        fb = self.fb
        for yy in range(y0, y1):
            o = (yy * W + x0) * 3
            fb[o:o + len(row)] = row

    def draw(self, snap):
        self.fb[:] = self.bg
        sx = lambda x: 40 + x * 12  # noqa: E731
        sy = lambda d: 170 + d * 17.67  # noqa: E731
        for n in snap["nodes"]:
            self.rect(sx(n["pos"][0]) - 14, 160, 28, 10, _rgb("#ec7fa3" if n["ready"] else "#6b4a3a"))
        for f in snap["fish"]:
            c = _rgb({"ca_loc": "#6f8f45", "ca_linh": "#d6e6f2", "ca_keo": "#d99a5b"}[f["kind"]])
            for i in range(3):
                self.rect(sx(f["pos"][0]) - 20 + i * 12, sy(f["pos"][1]) - 4 + (i % 2) * 6, 16, 8, c)
        for m in snap["monsters"]:
            self.rect(sx(m["pos"][0]) - 34, sy(m["pos"][1]) - 8, 68, 16, _rgb("#5d3f8c" if m["state"] == "chase" else "#3f5d33"))
        p = snap["player"]
        self.rect(sx(p["pos"][0]) - 11, sy(p["pos"][1]) - 20, 22, 40, _rgb("#3b6fb6"))
        self.rect(10, 8, W - 20, 100, b"\x1a\x20\x28")  # HUD
        for i in range(p["hp_max"]):
            self.rect(24 + i * 28, 20, 20, 20, _rgb("#e5484d") if i < p["hp"] else b"\x40\x40\x40")
        self.rect(70, 60, 220, 22, b"\x00\x00\x00")
        self.rect(70, 60, 220 * p["oxygen_ticks"] / p["oxygen_max_ticks"], 22, _rgb("#4fc3f7"))
        for i, it in enumerate(snap["hold"]):
            self.rect(790 + i * 20, 24, 16, 16, _rgb("#7bd389" if it["fresh"] >= 60 else "#f5c542" if it["fresh"] >= 30 else "#e5484d"))


def run_software(seed, duration, warmup, tuning):
    from .inputs import InputState
    from .runner import Session
    sess = Session("gather", tuning, {}, seed)
    rnd = SoftRenderer(tuning)
    idle = InputState((0.0, 0.0), {}, set())
    t0 = time.perf_counter()
    first_epoch = None
    frame_s, last, measured = [], None, 0.0
    while True:
        now = time.perf_counter()
        due = int((now - t0) * 60)  # sim chạy theo đồng hồ thật 60 tick/s, độc lập tốc độ vẽ
        while sess.tick < due and not sess.done:
            sess.step(idle)
        rnd.draw(sess.snapshot())
        now = time.perf_counter()
        if first_epoch is None:
            first_epoch = time.time()
        if last is not None and now - t0 >= warmup:
            frame_s.append(now - last)
            measured += now - last
            if measured >= duration:
                break
        last = now
    return frame_s, measured, first_epoch


def main(argv=None) -> int:
    start_epoch = _process_start_epoch()
    p = argparse.ArgumentParser(prog="chonoi.bench")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--warmup", type=float, default=3.0)
    p.add_argument("--renderer", choices=["auto", "browser", "software"], default="auto")
    a = p.parse_args(argv)
    if a.duration <= 0 or a.warmup < 0:
        sys.stderr.write("--duration phải > 0, --warmup ≥ 0\n")
        return 2
    from .contract import load_contract
    tuning = load_contract()["tuning"]
    used = None
    if a.renderer in ("auto", "browser"):
        try:
            res = run_browser(a.seed, a.duration, a.warmup, tuning)
            used = "browser"
        except Exception as e:  # không có Playwright/Chrome: dùng renderer phần mềm
            if a.renderer == "browser":
                sys.stderr.write(f"không chạy được renderer browser: {e}\n")
                return 1
            sys.stderr.write(f"bench: không dùng được trình duyệt ({type(e).__name__}: {e}); chuyển sang renderer software\n")
    if used is None:
        res = run_software(a.seed, a.duration, a.warmup, tuning)
        used = "software"
    out = metrics(res[0], res[1], res[2], start_epoch)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f)
        f.write("\n")
    sys.stderr.write(f"bench: renderer={used} {json.dumps(out)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

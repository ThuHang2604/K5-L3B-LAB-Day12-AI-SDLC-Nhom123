# Chụp ba cảnh báo (thủy quái gần, sắp hết oxy, khách sắp giận) ở chế độ thường và tương phản cao.
# Cần playwright + Chrome: python3 tools/ui_shots_hc.py "$PWD" docs/proof/phase-4/ui
import sys
import time

sys.path.insert(0, sys.argv[1])
from playwright.sync_api import sync_playwright  # noqa: E402

from chonoi.bench import _chrome_exe  # noqa: E402
from chonoi.contract import load_contract  # noqa: E402
from chonoi.live import LiveGame, LiveServer  # noqa: E402

tuning = load_contract()["tuning"]
out = sys.argv[2]
cases = {
    "gather-monster-oxygen": ("gather", {"player": {"pos": [56, 20], "oxygen_ticks": 400},
                                        "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 80}, {"id": "I2", "kind": "bong_sung", "fresh": 25}]}),
    "quan-angry": ("quan", {"random_customers": False,
                            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 90}, {"id": "I2", "kind": "bong_sung", "fresh": 20}],
                            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "patience_ticks_left": 700}]}),
}
errors = []
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=_chrome_exe(), args=["--no-sandbox"])
    for name, (mode, sc) in cases.items():
        for hc in (0, 1):
            game = LiveGame(mode, tuning, sc, 1)
            srv = LiveServer(game, port=0)
            srv.start()
            pg = b.new_page(viewport={"width": 1280, "height": 720})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"{srv.url}?contrast={hc}")
            time.sleep(1.0)
            pg.screenshot(path=f"{out}/{name}{'-hc' if hc else ''}.png")
            pg.close()
            srv.stop()
    b.close()
print("errors", errors)

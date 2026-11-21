# Chụp màn hình các màn UI (menu, DayIntro, gather, pause, EveningIntro, quan, DayResult, Shop, Summary) + đo FPS.
# Cần playwright + Chrome: python3 tools/ui_shots.py "$PWD" docs/proof/phase-2/ui
import sys, time, json, threading, urllib.request
sys.path.insert(0, sys.argv[1])
from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer
from playwright.sync_api import sync_playwright

tuning = load_contract()["tuning"]
sc = {"gather": {"hold": [{"id": f"I{i+1}", "kind": k, "fresh": f} for i, (k, f) in enumerate([("ca_loc", 100), ("ca_loc", 45), ("bong_sung", 100), ("bong_sung", 31), ("bong_sung", 100)])], "player": {"pos": [58, 18]}}}
game = LiveGame("day", tuning, sc, 3, days=1)
srv = LiveServer(game, port=0); srv.start()
base = f"http://127.0.0.1:{srv.port}"
def post(p, body=None):
    req = urllib.request.Request(base + p, data=json.dumps(body or {}).encode(), method="POST", headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()
def state(): return json.loads(urllib.request.urlopen(base + "/state").read())
out = sys.argv[2]
errors = []
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(base); time.sleep(1); pg.screenshot(path=f"{out}/1-menu.png")
    pg.keyboard.press("Enter"); time.sleep(0.6); pg.screenshot(path=f"{out}/2-dayintro.png")
    pg.keyboard.press("x"); time.sleep(0.3)
    pg.keyboard.down("s"); time.sleep(0.5); pg.keyboard.up("s"); time.sleep(1.5)
    pg.screenshot(path=f"{out}/3-gather.png")
    pg.keyboard.press("Escape"); time.sleep(0.4); pg.screenshot(path=f"{out}/4-pause.png")
    pg.keyboard.press("Escape"); time.sleep(0.3)
    # tới quán: dịch sim bằng cách cập bến không được (xa bến) -> đặt hết giờ bằng cách chạy nhanh
    with game._lock:
        game.session.sim.sub.time_left_ticks = 2
    time.sleep(0.5); pg.screenshot(path=f"{out}/5-evening.png")
    pg.keyboard.press("x"); time.sleep(0.3)
    with game._lock:
        sim = game.session.sim.sub
        for _ in range(130): 
            from chonoi.inputs import InputState
            game.session.step(InputState((0, 0), {}, set()))
        sim.pos = [3.0, 7.0]
    pg.keyboard.press("e"); time.sleep(0.3)
    with game._lock:
        for _ in range(1000):
            game.session.step(InputState((0, 0), {}, set()))
    time.sleep(0.5); pg.screenshot(path=f"{out}/6-quan.png")
    with game._lock:
        game.session.sim.sub.time_left_ticks = 2
    time.sleep(0.5); pg.screenshot(path=f"{out}/7-result.png")
    pg.keyboard.press("x"); time.sleep(0.5); pg.keyboard.press("1"); time.sleep(0.5)
    pg.screenshot(path=f"{out}/8-shop.png")
    pg.keyboard.press("Enter"); time.sleep(0.6); pg.screenshot(path=f"{out}/9-summary.png")
    # fps
    fps = pg.evaluate("""() => new Promise(r => { let n=0; const t0=performance.now(); function f(){ n++; if (performance.now()-t0<2000) requestAnimationFrame(f); else r(n/2); } requestAnimationFrame(f); })""")
    print("fps", fps)
    b.close()
srv.stop()
print("errors", errors)

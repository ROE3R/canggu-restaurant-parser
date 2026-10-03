#!/usr/bin/env python3
"""Multi-IP Grab sweep: 1 worker per ISP zone (5 IP berbeda). Resume-safe."""
from playwright.sync_api import sync_playwright
import json, csv, re, sys, os, time

OUT = "/home/agentuser/canggu-restaurant-parser/output/grab_sweep_final.jsonl"
CSV = "/home/agentuser/canggu_restaurants.csv"

ZONES = [
    ("isp_proxy11", __import__("os").environ.get("BD_PW","")),
    ("isp_proxy12", "hef25vp5t41v"),
    ("isp_proxy13", "03utein46j0z"),
    ("isp_proxy14", "tke6r17hjg40"),
    ("isp_proxy15", "14s88vrp5c8j"),
    ("isp_proxy16", "aq7dvv859c1y"),
    ("isp_proxy17", "rb9pe88a8lh1"),
    ("isp_proxy18", "5i86kn75jdga"),
    ("isp_proxy19", "9za1ehi3jj4w"),
]

def load_targets():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(line)["mid"])
            except Exception: pass
    targets = []
    for r in rows:
        u = (r.get("grabfood_url") or "").strip()
        m = re.search(r'/(6-C[A-Z0-9]{10,16})$', u.rstrip("/"))
        slug = re.search(r'/restaurant/([\w\-]+)/', u)
        if m and slug and m.group(1) not in done:
            targets.append((m.group(1), slug.group(1)))
    return targets

def run_worker(wid, zone, pw_, targets):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, proxy={
            "server": "http://brd.superproxy.io:22225",
            "username": f"brd-customer-hl_a5c1cc91-zone-{zone}-session-sw{wid}x{int(time.time())%10000}",
            "password": pw_},
            args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width":1366,"height":768}, locale="en-US")
        pg = ctx.new_page()
        pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        n = 0; skips = 0
        for mid, slug in targets:
            try:
                pg.goto(f"https://food.grab.com/id/en/restaurant/{slug}/{mid}", wait_until="domcontentloaded", timeout=50000)
                t = ""
                for _ in range(20):
                    pg.wait_for_timeout(2500)
                    t = pg.title()
                    if "GrabFood ID" not in t and "Oops" not in t and t.strip():
                        # double check store ready
                        has = pg.evaluate("""() => {
                            for (const k of ['__NEXT_REDUX_STORE__','__store']) {
                                const s = window[k];
                                if (s && s.getState) return Object.keys(s.getState().pageRestaurantDetail.entities||{}).length > 0;
                            }
                            return false;
                        }""")
                        if has: break
                if "GrabFood ID" in t or "Oops" in t or "ERROR" in t:
                    print(f"[{zone}] SKIP-IP: {mid}", flush=True)
                    skips += 1
                    if skips >= 3:
                        print(f"[{zone}] cooldown 300s", flush=True)
                        time.sleep(300); skips = 0
                    continue
                skips = 0
                out = pg.evaluate("""() => {
                    for (const k of ['__NEXT_REDUX_STORE__','__store']) {
                        const s = window[k];
                        if (s && s.getState) {
                            const e = s.getState().pageRestaurantDetail.entities;
                            const key = Object.keys(e)[0];
                            if (!key) return null;
                            const v = e[key];
                            return JSON.stringify({ID:v.ID,name:v.name,rating:v.rating,voteCount:v.voteCount,status:v.status,cuisine:v.cuisine,promo:v.promo,openingHours:v.openingHours,address:v.address});
                        }
                    }
                    return null;
                }""")
                if out:
                    with open(OUT, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"mid": mid, "url_slug": slug, "data": json.loads(out)}, ensure_ascii=False) + "\n")
                    n += 1
                    if n % 5 == 0: print(f"[{zone}] {n}/{len(targets)}", flush=True)
                else:
                    print(f"[{zone}] NOSTORE: {mid}", flush=True)
                    nsk = getattr(run_worker, "_nsk", 0) + 1
                    run_worker._nsk = nsk
                    if nsk % 5 == 0:
                        print(f"[{zone}] NOSTORE x5 — cooldown 180s", flush=True)
                        time.sleep(180)
            except Exception as e:
                print(f"[{zone}] ERR: {mid} {str(e)[:50]}", flush=True)
                try:
                    pg.close()
                    pg = ctx.new_page()
                    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
                except Exception: pass
        print(f"[{zone}] DONE: {n}", flush=True)
        b.close()

def main():
    my = int(os.environ.get("WID","0"))
    nw = int(os.environ.get("NW","5"))
    zone, pw_ = ZONES[my % len(ZONES)]
    targets = [t for i, t in enumerate(load_targets()) if i % nw == my]
    print(f"worker {my} zone {zone}: {len(targets)} targets", flush=True)
    run_worker(my, zone, pw_, targets)

if __name__ == "__main__":
    main()

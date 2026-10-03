#!/usr/bin/env python3
"""Bulk sweep Grab via category endpoint (30x lebih cepat dari playwright per-resto)."""
from playwright.sync_api import sync_playwright
import json as J, time, os, sys

OUT = "/home/agentuser/canggu-restaurant-parser/output/grab_bulk.jsonl"
LTLNGS = [
    "-8.6478,115.1385",  # Canggu
    "-8.6369,115.1555",  # Berawa
    "-8.6655,115.1400",  # Pererenan
    "-8.6700,115.1700",  # Cemagi
    "-8.6200,115.1700",  # Kerobokan/Umalas
    "-8.6500,115.1800",  # Tibubeneng
    "-8.7000,115.1900",  # Seseh
    "-8.6100,115.1400",  # Seminyak utara
]
CATS = list(range(1, 160))

def load_done():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try: done.add(J.loads(line)["mid"])
            except Exception: pass
    return done

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, proxy={"server":"http://brd.superproxy.io:22225",
        "username": f"brd-customer-{os.environ.get('BD_CUSTOMER','')}-zone-isp_proxy11-session-bulk002",
        "password": os.environ.get("BD_PW", "")}, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(user_agent="Mozilla/5.0 Chrome/131", locale="id-ID")
    cks = J.load(open("/tmp/cookies_dec.json"))
    cc = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path","/")} for c in cks if c["domain"].endswith("grab.com")]
    ctx.add_cookies(cc)
    pg = ctx.new_page()
    pg.goto("https://food.grab.com/id/en/", wait_until="domcontentloaded", timeout=70000)
    pg.wait_for_timeout(12000)
    done = load_done()
    print("done awal:", len(done))
    for ll in LTLNGS:
        for cat in CATS:
            offset = 0
            while True:
                try:
                    out = pg.evaluate("""async (args) => {
                        const [ll, cat, off] = args;
                        const u = `/proxy/foodweb/v2/order/category?latlng=${ll}&categoryShortcutID=${cat}&offset=${off}&pageSize=32`;
                        const r = await fetch(u, {credentials:'include', headers:{'Accept':'application/json'}});
                        if (r.status !== 200) return "ERR|" + r.status;
                        return await r.text();
                    }""", [ll, cat, offset])
                except Exception as e:
                    print("eval err", e); time.sleep(60); continue
                if out.startswith("ERR|"):
                    st = out.split("|")[1]
                    if st in ("429","401","502"):
                        print(f"[{ll} cat{cat}] status {st} — cooldown 120s")
                        time.sleep(120)
                        continue
                    break
                try:
                    j = J.loads(out)
                except Exception:
                    break
                sms = j.get("searchResult", {}).get("searchMerchants", [])
                added = 0
                with open(OUT, "a") as f:
                    for m in sms:
                        if m["id"] in done: continue
                        mb = m.get("merchantBrief", {})
                        f.write(J.dumps({"mid": m["id"], "bulk": True, "data": {
                            "ID": m["id"],
                            "name": m.get("address", {}).get("name",""),
                            "rating": mb.get("rating"),
                            "vote_count": mb.get("vote_count"),
                            "promo": mb.get("promo", {}).get("hasPromo"),
                            "cuisine": mb.get("cuisine"),
                            "openHours": mb.get("openHours"),
                            "address": m.get("address", {}).get("name"),
                            "estimatedDeliveryTime": m.get("estimatedDeliveryTime"),
                            "status": "ACTIVE",
                            "latlng": m.get("latlng"),
                        }}, ensure_ascii=False) + "\n")
                        done.add(m["id"]); added += 1
                print(f"[{ll} cat{cat} off{offset}] +{added} (total {len(done)})")
                offset += 32
                has_more = j.get("searchResult", {}).get("hasMore", False)
                if not has_more or not sms: break
                time.sleep(2)
    b.close()
print("BULK SWEEP DONE")

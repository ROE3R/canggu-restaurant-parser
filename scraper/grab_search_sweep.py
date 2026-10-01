#!/usr/bin/env python3
"""GrabFood search-based sweep: coverage + paid-slot (ads) detection. Canggu."""
import json, os, time
from playwright.sync_api import sync_playwright

OUT = "/home/agentuser/.hermes/cache/scratch/grab_search_sweep.json"
QUERIES = ["pizza", "sushi", "coffee", "burger", "nasi goreng", "ayam", "babu guling", "vegan",
           "mexican", "indian", "chinese", "seafood", "dessert", "smoothie", "bakery", "ramen",
           "poke", "taco", "steak", "pasta", "salad", "warung", "sate", "dim sum",
           "canggu", "berawa", "babakan", "pererenan", "tibubeneng", "batu bolong", "umalas", "kerobokan",
           "nasi campur", "babi guling", "bebek", "martabak", "bakso", "mie", "kwetiau", "nasi padang",
           "thai", "korean", "japanese", "italian", "french", "greek", "turkish", "vietnamese",
           "breakfast", "brunch", "lunch", "dinner", "healthy", "juice", "ice cream", "gelato",
           "bar", "beer", "wine", "cocktail", "bbq", "grill", "roast", "dumpling", "noodle", "rice bowl",
           "bubble tea", "matcha", "croissant", "donut", "crepe", "waffle", "soup", "curry", "kebab", "shawarma"]

data = json.load(open(OUT)) if os.path.exists(OUT) else {}
done_q = set(data.get("done_queries", []))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", locale="id-ID")
    page = ctx.new_page()
    ctx.add_cookies([{"name": "location", "value": json.dumps({"latitude": -8.6538, "longitude": 115.1385, "address": "Canggu", "countryCode": "ID", "isAccurate": True, "addressDetail": "", "noteToDriver": "", "city": "", "cityID": 0, "displayAddress": ""}), "domain": ".grab.com", "path": "/"}])
    resps = []
    def on_resp(r):
        if "guest/v2/search" in r.url:
            try: resps.append(r.text())
            except: pass
    page.on("response", on_resp)
    page.goto("https://food.grab.com/id/en/search", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(10000)

    for q in QUERIES:
        if q in done_q:
            continue
        resps.clear()
        inp = None
        for i in page.query_selector_all("input"):
            if i.is_visible(): inp = i; break
        if not inp:
            page.reload(timeout=60000, wait_until="domcontentloaded"); page.wait_for_timeout(9000)
            for i in page.query_selector_all("input"):
                if i.is_visible(): inp = i; break
        if not inp:
            print("NO INPUT, skip", q, flush=True); continue
        inp.click(); page.keyboard.press("Control+A"); inp.type(q, delay=50)
        page.keyboard.press("Enter")
        page.wait_for_timeout(9000)
        # scroll 2x utk lebih banyak
        for _ in range(2):
            page.mouse.wheel(0, 2500); page.wait_for_timeout(2500)
        page.wait_for_timeout(2000)
        merchants = []
        for b in resps:
            try:
                j = json.loads(b)
                for m in j["searchResult"]["searchMerchants"]:
                    merchants.append(m)
            except: pass
        # deteksi "Preferred Merchant" di DOM (label di card)
        pref_names = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a[href*="/restaurant/"]').forEach(a => {
                if ((a.textContent || '').includes('Preferred Merchant')) {
                    const nm = a.querySelector('div'); 
                    out.push((a.textContent || '').slice(0, 120));
                }
            });
            return out.slice(0, 10);
        }""")
        data.setdefault("queries", {})[q] = {
            "merchants": [{"id": m.get("id"), "name": (m.get("address") or {}).get("name"),
                            "rating": (m.get("merchantBrief") or {}).get("rating"),
                            "votes": (m.get("merchantBrief") or {}).get("vote_count"),
                            "address": (m.get("address") or {}).get("combined_address"),
                            "cuisine": (m.get("merchantBrief") or {}).get("cuisine"),
                            "order": i} for i, m in enumerate(merchants)],
            "preferred_dom": pref_names,
        }
        done_q.add(q)
        data["done_queries"] = sorted(done_q)
        json.dump(data, open(OUT, "w"))
        print(f"[{len(done_q)}/{len(QUERIES)}] {q}: {len(merchants)} merchants, pref_dom={len(pref_names)}", flush=True)
        time.sleep(2)
    browser.close()
print("DONE", flush=True)

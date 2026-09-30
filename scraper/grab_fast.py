#!/usr/bin/env python3
"""GrabFood fast grab: let the app init itself, steal its session token,
call the search API in-page with it, sweep keywords, save all JSON.
"""
import json, time, os, sys
from playwright.sync_api import sync_playwright

OUT = "/home/agentuser/canggu-restaurant-parser/output"
os.makedirs(OUT, exist_ok=True)
LAT, LNG = -8.6478, 115.1385
KEYWORDS = ["", "warung", "cafe", "restaurant", "pizza", "sushi", "bakery", "bar",
            "breakfast", "coffee", "burger", "thai", "japanese", "italian",
            "indonesian", "vegan", "seafood", "grill", "dessert", "juice",
            "mexican", "indian", "korean", "steak", "nasi", "ayam", "babi",
            "smoothie", "sandwich", "ramen"]

DUMP_JS = "() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))"

SEARCH_JS = """
async (args) => {
  const [kw, token] = args;
  const out = [];
  for (let page = 0; page < 3; page++) {
    const body = {
      searchType: "restaurantDelivery",
      latlng: "%f,%f",
      keyword: kw,
      offset: page * 32,
      pageSize: 32,
      countryCode: "ID",
      enableGuestEndpoints: true
    };
    try {
      const r = await fetch("/proxy/foodweb/guest/v2/search", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Authorization": "Bearer " + token},
        credentials: "include",
        body: JSON.stringify(body)
      });
      const txt = await r.text();
      if (r.status !== 200) { out.push({kw, page, status: r.status, body: txt.slice(0,200)}); break; }
      out.push({kw, page, status: 200, body: txt});
      let n = 0;
      try { n = (JSON.parse(txt).searchResult && JSON.parse(txt).searchResult.merchants || []).length; } catch(e){}
      if (n < 32) break;
    } catch (e) { out.push({kw, page, status: -1, body: String(e)}); break; }
  }
  return out;
}
""" % (LAT, LNG)


def grab_token_from_app(page):
    """Navigate the app, wait for it to init, dump sessionStorage keys."""
    for attempt in range(4):
        try:
            page.goto("https://food.grab.com/id/en/restaurants?search=canggu",
                      wait_until="domcontentloaded", timeout=80000)
            page.wait_for_timeout(9000)
            ss = json.loads(page.evaluate(DUMP_JS))
            # look for JWT-looking values
            cands = {k: v for k, v in ss.items() if v and v.count(".") == 2 and len(v) > 100}
            if cands:
                return cands
            print(f"  attempt {attempt+1}: sessionStorage keys={list(ss.keys())}", flush=True)
        except Exception as e:
            print(f"  attempt {attempt+1} nav err: {str(e)[:70]}", flush=True)
        time.sleep(4)
    return {}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            proxy={"server": "http://proxy.hypeproxy.site:1012",
                   "username": "user9", "password": "pWNm5MVEM70W"},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            geolocation={"latitude": LAT, "longitude": LNG},
            permissions=["geolocation"], locale="en-US",
            viewport={"width": 1366, "height": 900})
        # seed location cookie for Canggu
        loc = json.dumps({"latitude": LAT, "longitude": LNG, "address": "Canggu, Bali",
                          "countryCode": "ID", "isAccurate": True, "addressDetail": "",
                          "noteToDriver": "", "city": "Badung", "cityID": 0, "displayAddress": ""})
        ctx.add_cookies([
            {"name": "location", "value": loc, "domain": ".grab.com", "path": "/"},
            {"name": "gfc_country", "value": "ID", "domain": ".grab.com", "path": "/"},
        ])
        page = ctx.new_page()

        tokens = grab_token_from_app(page)
        if not tokens:
            print("NO TOKEN — abort", flush=True)
            browser.close(); sys.exit(1)
        token = list(tokens.values())[0]
        print(f"token ok: {len(token)} chars", flush=True)

        all_rows = {}
        raw_dir = "/home/agentuser/.hermes/cache/scratch/grab_api_responses"
        os.makedirs(raw_dir, exist_ok=True)
        for kw in KEYWORDS:
            try:
                results = page.evaluate(SEARCH_JS, [kw, token])
            except Exception as e:
                print(f"  {kw!r}: eval err {str(e)[:60]}", flush=True)
                continue
            got = 0
            for res in results:
                if res["status"] == 200:
                    fn = os.path.join(raw_dir, f"kw_{kw or 'all'}_p{res['page']}.json")
                    with open(fn, "w") as f:
                        json.dump(json.loads(res["body"]), f)
                    try:
                        merchants = json.loads(res["body"]).get("searchResult", {}).get("merchants", [])
                    except Exception:
                        merchants = []
                    for m in merchants:
                        mid = m.get("id") or m.get("merchantID") or m.get("name")
                        if mid and mid not in all_rows:
                            all_rows[mid] = m
                    got += len(merchants)
                else:
                    print(f"  {kw!r} p{res['page']}: HTTP {res['status']} {res['body'][:80]}", flush=True)
            print(f"kw={kw!r}: +{got} merchants (total {len(all_rows)})", flush=True)
            time.sleep(1.2)
        browser.close()

    with open(os.path.join(OUT, "grabfood_raw.json"), "w") as f:
        json.dump(list(all_rows.values()), f, ensure_ascii=False, indent=1)
    print(f"\nSAVED {len(all_rows)} unique GrabFood merchants", flush=True)


if __name__ == "__main__":
    main()

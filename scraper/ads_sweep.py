#!/usr/bin/env python3
"""Ads badge full sweep: open Maps search per query in a real browser, read the
feed cards, mark every place whose card shows 'Sponsored'."""
import json, time, os
from playwright.sync_api import sync_playwright

QUERIES = [
    "restaurants canggu", "restaurant batu bolong canggu", "cafe batu bolong",
    "restaurant berawa canggu", "cafe berawa canggu", "warung canggu bali",
    "restaurant pererenan", "cafe pererenan", "restaurant sido bangkou",
    "restaurant padonan", "restaurant babakan canggu",
    "sushi canggu", "pizza canggu", "bakery canggu", "bar canggu bali",
    "breakfast canggu", "grill canggu", "vegan canggu", "eatery canggu",
    "indonesian restaurant canggu", "italian restaurant canggu", "mexican canggu",
    "seafood canggu", "steakhouse canggu", "coffee canggu", "juice canggu",
    "thai food canggu", "japanese restaurant canggu", "indian food canggu",
]
OUT = "/home/agentuser/.hermes/cache/scratch/ads_by_name.json"
OUT_PID = "/home/agentuser/.hermes/cache/scratch/ads_by_pid.json"

EXTRACT_JS = """
() => {
  const out = [];
  const seen = new Set();
  document.querySelectorAll('a.hfpxzc').forEach(a => {
    const card = a.closest('div.Nv2PK') || a.closest('div[jsaction]');
    const name = a.getAttribute('aria-label') || '';
    if (!name || seen.has(name)) return;
    seen.add(name);
    let sponsored = false;
    if (card) {
      const t = card.innerText || '';
      if (/(^|\\n)\\s*(Sponsored|Bersponsor|Iklan)\\s*(\\n|$)/i.test(t)) sponsored = true;
    }
    // extract place_id/cid from the maps URL
    const href = a.getAttribute('href') || '';
    const m = href.match(/!1s(0x[0-9a-f]+:0x[0-9a-f]+)/) || href.match(/place\\/([^/@?]+)/);
    out.push({name, sponsored, cid: m ? m[1] : null, href});
  });
  return out;
}
"""

def main():
    ads = json.load(open(OUT)) if os.path.exists(OUT) else {}
    places = json.load(open("/home/agentuser/.hermes/cache/scratch/places_enriched.json"))
    # name -> pid index (normalized)
    def norm(n): return (n or "").lower().strip()
    name2pid = {norm(p.get("name")): p.get("pid") for p in places}

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = b.new_context(locale="en-US", viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        pg = ctx.new_page()
        for i, q in enumerate(QUERIES, 1):
            try:
                pg.goto(f"https://www.google.com/maps/search/{q.replace(' ', '+')}?hl=en",
                        wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(5000)
                for _ in range(2):
                    pg.evaluate("""() => { const f = document.querySelector('div[role="feed"]'); if (f) f.scrollTop = f.scrollHeight; }""")
                    pg.wait_for_timeout(2000)
                cards = pg.evaluate(EXTRACT_JS)
                n_ads = 0
                for c in cards:
                    if c["sponsored"]:
                        pid = name2pid.get(norm(c["name"]))
                        if pid:
                            ads[pid] = {"query": q, "name": c["name"]}
                            n_ads += 1
                print(f"[{i}/{len(QUERIES)}] {q}: {len(cards)} cards, {n_ads} new ads (total {len(ads)})", flush=True)
                json.dump(ads, open(OUT, "w"), ensure_ascii=False, indent=1)
            except Exception as e:
                print(f"[{i}] {q} ERR {str(e)[:80]}", flush=True)
            time.sleep(2)
        b.close()
    print(f"DONE: {len(ads)} places with ads badge", flush=True)

if __name__ == "__main__":
    main()

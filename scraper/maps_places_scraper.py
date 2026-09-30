#!/usr/bin/env python3
"""Google Maps place discovery via internal /search?tbm=map JSON API.
Run from inside a Maps page context (Playwright). Grid of queries -> place records.
"""
import json, time, sys
from playwright.sync_api import sync_playwright

QUERIES = [
    # sub-areas
    "restaurants canggu", "restaurant batu bolong canggu", "cafe batu bolong",
    "restaurant berawa canggu", "cafe berawa canggu", "warung canggu bali",
    "restaurant pererenan", "cafe pererenan", "restaurant sido bangkou",
    "restaurant padonan", "restaurant tiying tutul", "restaurant babakan canggu",
    # categories
    "sushi canggu", "pizza canggu", "bakery canggu", "bar canggu bali",
    "breakfast canggu", "grill canggu", "vegan canggu", "eatery canggu",
    "indonesian restaurant canggu", "italian restaurant canggu", "mexican canggu",
    "seafood canggu", "steakhouse canggu", "coffee canggu", "juice canggu",
    "thai food canggu", "japanese restaurant canggu", "indian food canggu",
]

SETUP_JS = """
(qs) => {
  window.__Q = qs; window.__IDX = 0; window.__DONE = false;
  window.__RESULTS = []; window.__LOG = [];
  window.__PB = "!4m12!1m3!1d1000!2d115.1385!3d-8.6478!2m3!1f0!2f0!3f0!3m2!1i1366!2i900!4f13.1!7i20!10b1!12m4!1b1!2m2!1e2!2b1!3e1!4b1!14b1!18m5!3b1!4b1!5b1!6b1!7b1!19b1!20m2!1e2!2b1!21b1!22b1!25b1!26b1!30m1!2b1!33m1!2b1!35b1";
  window.__PARSE = (raw) => {
    const d = JSON.parse(raw.replace(/^\\)\\]\\}'\\n?/, ''));
    const places = [];
    function scan(n, depth) {
      if (depth > 15 || !n) return;
      if (Array.isArray(n)) {
        if (n.length > 100 && typeof n[11] === 'string' && typeof n[78] === 'string' && n[78].startsWith('ChIJ')) {
          let phone = null, website = null;
          try { phone = n[178] && n[178][0]; } catch(e){}
          try { website = n[7] && n[7][0]; } catch(e){}
          places.push({name: n[11], rating: n[4]?n[4][7]:null, lat: n[9]?n[9][2]:null,
                       lng: n[9]?n[9][3]:null, cats: n[13]||[], addr: n[39]||n[18]||null,
                       phone, website, pid: n[78], cid: n[10]});
        }
        n.forEach(c => scan(c, depth+1));
      } else if (typeof n === 'object') Object.keys(n).forEach(k => scan(n[k], depth+1));
    }
    scan(d, 0);
    return places;
  };
  const step = async () => {
    if (window.__DONE) return;
    const q = window.__Q[window.__IDX];
    if (q === undefined) { window.__DONE = true; return; }
    try {
      const res = await fetch("/search?tbm=map&authuser=0&hl=en&gl=id&q=" +
        encodeURIComponent(q) + "&pb=" + encodeURIComponent(window.__PB));
      const t = await res.text();
      window.__RESULTS.push(...window.__PARSE(t));
      window.__LOG.push(q + "->" + window.__RESULTS.length);
    } catch(e) { window.__LOG.push(q + " ERR"); }
    window.__IDX++;
    setTimeout(step, 2000);
  };
  step();
  return 'started';
}
"""

def main(out="/home/agentuser/canggu-restaurant-parser/output/maps_places_raw.jsonl"):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = b.new_context(locale="en-US", viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        pg = ctx.new_page()
        pg.goto("https://www.google.com/maps/search/restaurants+in+canggu+bali?hl=en",
                wait_until="domcontentloaded", timeout=80000)
        pg.wait_for_timeout(5000)
        pg.evaluate(SETUP_JS, QUERIES)
        for _ in range(60):
            time.sleep(6)
            if pg.evaluate("!!window.__DONE"):
                break
        results = pg.evaluate("JSON.stringify(window.__RESULTS||[])")
        b.close()
    places = json.loads(results)
    with open(out, "w") as f:
        for p_ in places:
            f.write(json.dumps(p_, ensure_ascii=False) + "\n")
    print(f"{len(places)} place rows -> {out}")

if __name__ == "__main__":
    main(*sys.argv[1:])

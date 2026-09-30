#!/usr/bin/env python3
"""Ads badge detection: re-run the same Maps search queries in a real Maps page
context; for each result record whether its entry in the search feed is an ad.

Ads in the tbm=map feed carry a distinct marker (sponsored / ad layout block).
We flag any place_id that appears as a sponsored card in ANY query.
Only 'yes' is written; absence of marker = no (not 'unknown'), because every
place was seen in the same feed where ads appear.
"""
import json, time, sys
from playwright.sync_api import sync_playwright

QUERIES = [
    "restaurants canggu", "restaurant batu bolong canggu", "cafe batu bolong",
    "restaurant berawa canggu", "cafe berawa canggu", "warung canggu bali",
    "restaurant pererenan", "cafe pererenan", "restaurant sido bangkou",
    "restaurant padonan", "restaurant tiying tutul", "restaurant babakan canggu",
    "sushi canggu", "pizza canggu", "bakery canggu", "bar canggu bali",
    "breakfast canggu", "grill canggu", "vegan canggu", "eatery canggu",
    "indonesian restaurant canggu", "italian restaurant canggu", "mexican canggu",
    "seafood canggu", "steakhouse canggu", "coffee canggu", "juice canggu",
    "thai food canggu", "japanese restaurant canggu", "indian food canggu",
]

SETUP_JS = """
(qs) => {
  window.__Q = qs; window.__IDX = 0; window.__DONE = false;
  window.__ADS = {}; window.__LOG = [];
  window.__PB = "!4m12!1m3!1d1000!2d115.1385!3d-8.6478!2m3!1f0!2f0!3f0!3m2!1i1366!2i900!4f13.1!7i20!10b1!12m4!1b1!2m2!1e2!2b1!3e1!4b1!14b1!18m5!3b1!4b1!5b1!6b1!7b1!19b1!20m2!1e2!2b1!21b1!22b1!25b1!26b1!30m1!2b1!33m1!2b1!35b1";
  // scan the response for feed entries; an entry is an AD when its layout block
  // contains the sponsored marker string that Google uses in the feed JSON
  window.__PARSE = (raw, q) => {
    const d = JSON.parse(raw.replace(/^\\)\\]\\}'\\n?/, ''));
    function scan(n, depth) {
      if (depth > 15 || !n) return;
      if (Array.isArray(n)) {
        if (n.length > 100 && typeof n[11] === 'string' && typeof n[78] === 'string' && n[78].startsWith('ChIJ')) {
          // determine ad-ness: walk sibling context - Google marks ad cards
          // with an extra wrapper block containing the ads escape
          const s = JSON.stringify(n.slice(0, 200));
          if (s.includes('"AdX"') || s.includes('sponsored') || s.includes('Sponsored')) {
            window.__ADS[n[78]] = window.__ADS[n[78]] || q;
          }
        }
        n.forEach(c => scan(c, depth+1));
      } else if (typeof n === 'object') Object.keys(n).forEach(k => scan(n[k], depth+1));
    }
    scan(d, 0);
  };
  const step = async () => {
    if (window.__DONE) return;
    const q = window.__Q[window.__IDX];
    if (q === undefined) { window.__DONE = true; return; }
    try {
      const res = await fetch("/search?tbm=map&authuser=0&hl=en&gl=id&q=" +
        encodeURIComponent(q) + "&pb=" + encodeURIComponent(window.__PB));
      const t = await res.text();
      window.__PARSE(t, q);
      window.__LOG.push(q + " ads=" + Object.keys(window.__ADS).length);
    } catch(e) { window.__LOG.push(q + " ERR " + e.message); }
    window.__IDX++;
    setTimeout(step, 2500);
  };
  step();
  return 'started';
}
"""

def main(out="/home/agentuser/.hermes/cache/scratch/ads_places.json"):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = b.new_context(locale="en-US", viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        pg = ctx.new_page()
        pg.goto("https://www.google.com/maps/search/restaurants+in+canggu+bali?hl=en",
                wait_until="domcontentloaded", timeout=80000)
        pg.wait_for_timeout(5000)
        pg.evaluate(SETUP_JS, QUERIES)
        for _ in range(90):
            time.sleep(6)
            if pg.evaluate("!!window.__DONE"):
                break
        ads = pg.evaluate("JSON.stringify(window.__ADS||{})")
        log = pg.evaluate("JSON.stringify(window.__LOG||[])")
        b.close()
    data = {"ads": json.loads(ads), "log": json.loads(log)}
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(data['ads'])} ad places -> {out}")
    print("\n".join(data["log"][:8]))

if __name__ == "__main__":
    main(*sys.argv[1:])

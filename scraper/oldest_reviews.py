#!/usr/bin/env python3
"""Fast oldest-review-date scraper: N parallel Chromium tabs via HTTP proxy.
Each tab: open place -> open reviews -> sort by oldest -> grab first review date.
"""
import json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

PROXY = {"server": "http://proxy.hypeproxy.site:1012", "username": os.environ.get("PX_USER", "user9"), "password": os.environ.get("PX_PASS", "")}
IN_FILE = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
WORKERS = 5

def load_state():
    if os.path.exists(OUT_FILE):
        return json.load(open(OUT_FILE))
    return {}

def save_state(state):
    json.dump(state, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)

def scrape_one(pid):
    """Return oldest review date string or None."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:  # one browser per worker-call is slow; instead reuse - see worker()
        pass

def main():
    places = json.load(open(IN_FILE))
    todo = [p for p in places if p.get("pid") and p.get("review_count")]
    state = load_state()
    todo = [p for p in todo if p["pid"] not in state or not state[p["pid"]].get("oldest_review")]
    print(f"{len(todo)} places to scrape (workers={WORKERS})", flush=True)
    if not todo:
        print("ALL DONE"); return

    def worker(chunk):
        results = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, proxy=PROXY, args=["--no-sandbox"])
            ctx = browser.new_context(
                locale="en-US",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
            page = ctx.new_page()
            # pre-consent
            try:
                page.goto("https://www.google.com/?hl=en&consent=true", timeout=30000)
                page.wait_for_timeout(1500)
            except Exception:
                pass
            for p in chunk:
                pid = p["pid"]
                rec = {"oldest_review": None, "newest_review": None, "status": "fail"}
                for attempt in range(2):
                    try:
                        page.goto(f"https://www.google.com/maps/place/?q=place_id:{pid}&hl=en",
                                  timeout=35000, wait_until="domcontentloaded")
                        page.wait_for_timeout(4000)
                        # check full view: reviews button exists
                        btn = page.locator("button:has-text('Reviews'), button[aria-label*='Reviews']").first
                        if btn.count() == 0:
                            # maybe body contains 'Limited View'
                            rec["status"] = "limited"
                            break
                        btn.click()
                        page.wait_for_timeout(2500)
                        # sort menu
                        sortbtn = page.locator("button:has-text('Sort'), button[data-value='Sort']").first
                        if sortbtn.count():
                            sortbtn.click()
                            page.wait_for_timeout(1200)
                            oldest = page.locator("button:has-text('Oldest')").first
                            if oldest.count():
                                oldest.click()
                                page.wait_for_timeout(2500)
                        # grab visible review dates (relative dates like "a year ago" or exact)
                        dates = page.eval_on_selector_all(
                            "div[class*='jftiEf'] span[class*='xRkPPb'], span[data-source-date], div[data-review-id] span[class*='xRkPPb']",
                            "els => els.map(e => e.textContent)")
                        if not dates:
                            dates = page.eval_on_selector_all(
                                "span[class*='xRkPPb']", "els => els.map(e => e.textContent)")
                        if dates:
                            rec["newest_review"] = dates[0]
                            rec["oldest_review"] = dates[-1]
                            rec["status"] = "ok"
                            break
                        else:
                            rec["status"] = "nodates"
                    except Exception as e:
                        if attempt == 1:
                            rec["status"] = "err"
                results[pid] = rec
                if len(results) % 5 == 0:
                    print(f"  worker chunk: {len(results)} done", flush=True)
            browser.close()
        return results

    # chunk places into WORKERS groups
    chunks = [todo[i::WORKERS] for i in range(WORKERS)]
    all_results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for res in ex.map(worker, chunks):
            all_results.update(res)
            # merge-save incrementally
            state.update(res)
            save_state(state)
    ok = sum(1 for v in all_results.values() if v.get("status") == "ok")
    print(f"DONE: {ok}/{len(todo)} oldest dates captured", flush=True)

if __name__ == "__main__":
    main()

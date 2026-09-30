#!/usr/bin/env python3
"""GrabFood: in-page guest login then search via page fetch with bearer token."""
import json, sys, time, os
from playwright.sync_api import sync_playwright

OUT = "/home/agentuser/.hermes/cache/scratch/grab_captured"
os.makedirs(OUT, exist_ok=True)
LAT, LNG = -8.6478, 115.1385
QUERIES = ["", "warung", "cafe", "bar", "pizza", "sushi", "bakery", "canggu"]

LOGIN_JS = """
async () => {
  try {
    const r = await fetch("/proxy/authnv4/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "include",
      body: JSON.stringify({clientID: "crab-web", deviceID: "guest-" + Math.random().toString(36).slice(2), language: "en", countryCode: "ID"})
    });
    const j = await r.json();
    return {status: r.status, token: j.displayToken || null};
  } catch (e) { return {status: -1, token: null, err: String(e)}; }
}
"""

SEARCH_JS = """
async (args) => {
  const [kw, lat, lng, token] = args;
  const body = {
    searchType: "restaurantDelivery",
    latlng: lat + "," + lng,
    keyword: kw,
    offset: 0, pageSize: 32,
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
    return {status: r.status, body: txt.slice(0, 300000)};
  } catch (e) { return {status: -1, body: String(e)}; }
}
"""

def run(queries, headless=True):
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless,
            proxy={"server": "socks5://127.0.0.1:1080"},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            geolocation={"latitude": LAT, "longitude": LNG},
            permissions=["geolocation"], locale="en-US",
            viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        def nav(url, tries=5):
            for t in range(tries):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=80000)
                    return True
                except Exception as e:
                    print(f"nav retry {t+1}: {str(e)[:70]}", flush=True)
                    time.sleep(4)
            return False

        if not nav("https://food.grab.com/id/en/"):
            print("FAILED to load grab", flush=True)
            browser.close(); return {}
        page.wait_for_timeout(6000)

        login = page.evaluate(LOGIN_JS)
        token = login.get("token")
        print("login:", login.get("status"), "token len:", len(token) if token else 0, flush=True)
        if not token:
            print("NO TOKEN, abort"); browser.close(); return {}

        for kw in queries:
            res = page.evaluate(SEARCH_JS, [kw, str(LAT), str(LNG), token])
            print(f"kw={kw!r} -> {res['status']} len {len(res['body'])}", flush=True)
            if res["status"] == 200:
                results[kw or "_all"] = res["body"]
            time.sleep(1.5)
        browser.close()

    stamp = int(time.time())
    with open(f"{OUT}/search_results_{stamp}.json", "w") as f:
        json.dump(results, f)
    print(f"saved {len(results)} searches")
    return results

if __name__ == "__main__":
    run(QUERIES)

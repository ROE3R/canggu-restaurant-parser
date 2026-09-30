#!/usr/bin/env python3
"""Crawl each restaurant's website to extract email + social links.
Free (no API). Parallel. Resumable. Honest: only what's actually on the page.
"""
import json, os, re, time
from concurrent.futures import ThreadPoolExecutor
import requests

IN_FILE = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/website_contacts.json"
MAX_WORKERS = 12
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
BAD_EMAIL = ("example.com", "sentry", "wixpress", "gstatic", "googleapis",
             ".png", ".jpg", ".jpeg", ".webp", ".svg", "domain.com", "email.com",
             "yourdomain", "sentry.io", "w3.org", "schema.org")
SOCIAL_PATTERNS = {
    "instagram": re.compile(r'instagram\.com/([A-Za-z0-9_.]{3,30})'),
    "facebook": re.compile(r'facebook\.com/([A-Za-z0-9_.\-]{3,40})'),
    "tiktok": re.compile(r'tiktok\.com/@([A-Za-z0-9_.]{3,30})'),
}
CONTACT_PATHS = ["", "/contact", "/contact-us", "/about", "/about-us", "/kontak", "/hubungi"]

def clean_page(raw, base):
    """Return (emails, socials) found in HTML."""
    # decode basic entities
    html = raw.replace("&#64;", "@").replace("&commat;", "@")
    emails = set()
    for e in EMAIL_RE.findall(html):
        el = e.lower()
        if any(b in el for b in BAD_EMAIL):
            continue
        emails.add(e)
    socials = {}
    for name, pat in SOCIAL_PATTERNS.items():
        for m in pat.findall(html):
            ml = m.lower()
            if ml in ("sharer", "share", "tr", "plugins", "dialog", "profile.php",
                      "pages", "watch", "p", "hashtag", "explore"):
                continue
            socials.setdefault(name, set()).add(m.rstrip("/."))
    return emails, {k: sorted(v) for k, v in socials.items()}

def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en,id"},
                         timeout=timeout, allow_redirects=True, verify=False)
        if r.status_code == 200 and "text" in (r.headers.get("Content-Type") or "text"):
            return r.text[:400000], r.url
    except Exception:
        pass
    return None, url

def scrape_site(website):
    out = {"emails": [], "instagram": [], "facebook": [], "tiktok": [], "pages_tried": 0}
    if not website or not website.startswith("http"):
        return out
    base = website.rstrip("/")
    found_em, found_soc = set(), {}
    for path in CONTACT_PATHS:
        url = base + path if path else base
        html, final = fetch(url)
        out["pages_tried"] += 1
        if html:
            em, soc = clean_page(html, final)
            found_em |= em
            for k, v in soc.items():
                found_soc.setdefault(k, set()).update(v)
            # mailto links are the strongest signal
            for m in re.findall(r'mailto:([^"\'>\s?]+)', html, re.I):
                if not any(b in m.lower() for b in BAD_EMAIL):
                    found_em.add(m)
        if found_em and found_soc.get("instagram"):
            break
        time.sleep(0.2)
    out["emails"] = sorted(found_em)[:3]
    for k in ("instagram", "facebook", "tiktok"):
        out[k] = sorted(found_soc.get(k, []))[:2]
    return out

def main():
    import urllib3
    urllib3.disable_warnings()
    places = json.load(open(IN_FILE))
    state = json.load(open(OUT_FILE)) if os.path.exists(OUT_FILE) else {}
    todo = [p for p in places if p.get("website") and p["pid"] not in state]
    print(f"{len(places)} places, {len(todo)} websites to crawl", flush=True)

    def work(p):
        return p["pid"], scrape_site(p.get("website"))

    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for pid, res in ex.map(work, todo):
            state[pid] = res
            done += 1
            if done % 20 == 0:
                json.dump(state, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
                ne = sum(1 for v in state.values() if v.get("emails"))
                print(f"  {done}/{len(todo)} crawled, {ne} with email", flush=True)
    json.dump(state, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
    ne = sum(1 for v in state.values() if v.get("emails"))
    ni = sum(1 for v in state.values() if v.get("instagram"))
    print(f"DONE: {len(state)} sites, {ne} with email, {ni} with instagram", flush=True)

if __name__ == "__main__":
    main()

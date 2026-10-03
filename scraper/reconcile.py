#!/usr/bin/env python3
"""Reconcile CSV with verification results (displayName verify + POI search)."""
import csv, json, re, sys
sys.path.insert(0, "/home/agentuser/canggu-restaurant-parser")
import pipeline

ROOT = "/home/agentuser/canggu-restaurant-parser"
rows = list(csv.DictReader(open(ROOT+"/output/canggu_restaurants.csv", encoding="utf-8")))

# --- sumber 1: displayName verify (gofood_url benar/salah)
disp = {}
for line in open(ROOT+"/output/gf_verify.jsonl"):
    rec = json.loads(line)
    disp[rec["uid"]] = rec

# --- sumber 2: POI (keberadaan resmi by name)
poi = {}
for line in open(ROOT+"/output/gf_poi.jsonl"):
    rec = json.loads(line)
    poi[rec["name"]] = rec

GENERIC = {"canggu","bali","badung","kerobokan","berawa","pantai","batu","bolong","umalas",
           "seminyak","kuta","utara","restaurant","cafe","warung","the","and","dan",
           "breakfast","dinner","food","indonesia","bar","kitchen","grill","bakery","eatery",
           "beach","road","jalan","jl","no","street","jln"}
def name_tokens(s):
    return set(t.lower() for t in re.split(r"[\s&,\-()|]+", s or "") if len(t) > 2) - GENERIC

fixed, blanked, kept = 0, 0, 0
for r in rows:
    uid = pipeline.gofood_uid(r.get("gofood_url"))
    v = disp.get(uid)
    if not uid or not v:
        continue
    if v.get("ok") and v.get("official_name"):
        # cek nama resmi mirip nama maps?
        mt, ot = name_tokens(r["name"]), name_tokens(v["official_name"])
        if mt & ot:
            kept += 1
            # perbarui URL ke versi kanonik tanpa /en/ :443
            canon = v["url"]
            r["gofood_url"] = canon
            # simpan nama resmi di note
            note = (r.get("data_notes") or "")
            if "gofood_name=" not in note:
                r["data_notes"] = (note + ("; " if note else "") + "gofood_name=" + v["official_name"]).strip()
        else:
            # MISMATCH: coba POI match utk repair
            p = poi.get(r["name"])
            fixed += 1
            r["gofood_url"] = ""  # url lama salah — kosongkan
            r["gofood_rating"] = r["gofood_votes"] = ""
            r["gofood_rating_2026"] = r["gofood_votes_2026"] = ""
            r["gofood_since"] = r["gofood_badges"] = r["gofood_maf"] = ""
            r["gofood_review_count_window"] = r["gofood_review_newest"] = r["gofood_review_oldest_window"] = r["gofood_review_sample"] = ""
            note = (r.get("data_notes") or "").replace("gofood_name=" + v["official_name"], "")
            r["data_notes"] = (note + ("; " if note else "") +
                f"gofood_url removed (was pointing to '{v['official_name']}'); re-check").strip("; ").strip()
    elif v.get("error", "").startswith("errorCode 404"):
        blanked += 1
        # 404 = not found at check date; kosongkan field gofood aktif, keep URL utk arsip? ->
        # konsisten: kosongkan data, URL dipertahankan dengan note
        for c in ["gofood_rating","gofood_votes","gofood_rating_2026","gofood_votes_2026",
                  "gofood_since","gofood_badges","gofood_maf",
                  "gofood_review_count_window","gofood_review_newest",
                  "gofood_review_oldest_window","gofood_review_sample"]:
            r[c] = ""
        note = r.get("data_notes") or ""
        if "not_found_on_gofood" not in note:
            r["data_notes"] = (note + ("; " if note else "") + "not_found_on_gofood_at_2026-10-02_may_be_temporary").strip()

# --- dedup gofood uid: uid dipakai >1 row dan tidak match namanya = wrong match sisa
import collections
def _uid(u):
    m = re.search(r'-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', u or "")
    return m.group(1) if m else None
uid_count = collections.Counter(_uid(r["gofood_url"]) for r in rows if r["gofood_url"])
for r in rows:
    k = _uid(r["gofood_url"])
    if k and uid_count[k] > 1:
        v = disp.get(k)
        if v and v.get("ok") and v.get("official_name"):
            if not (name_tokens(r["name"]) & name_tokens(v["official_name"])):
                r["gofood_url"] = ""
                for c in ["gofood_rating","gofood_votes","gofood_rating_2026","gofood_votes_2026",
                          "gofood_since","gofood_badges","gofood_maf",
                          "gofood_review_count_window","gofood_review_newest",
                          "gofood_review_oldest_window","gofood_review_sample"]:
                    r[c] = ""
                note = r.get("data_notes") or ""
                r["data_notes"] = (note + ("; " if note else "") +
                    f"gofood_url removed (was pointing to '{v['official_name']}'); re-check").strip("; ").strip()
            else:
                note = r.get("data_notes") or ""
                if "same_outlet_as" not in note:
                    r["data_notes"] = (note + ("; " if note else "") + "same_gofood_outlet").strip()

with open(ROOT+"/output/canggu_restaurants.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"kept={kept} mismatch_blanked={fixed} not_found_blanked={blanked}")

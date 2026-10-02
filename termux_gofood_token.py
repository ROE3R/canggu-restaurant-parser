#!/data/data/com.termux/files/usr/bin/python3
"""
gofood_token.py — Ambil token Gojek dari HP sendiri (Termux, tanpa root).
Cara kerja: login GoID pakai nomor HP kamu sendiri → OTP WhatsApp masuk ke HP-mu →
ketik OTP → script dapat access_token → otomatis tes akses GoFood & tampilkan token.

INSTALL (sekali):
  pkg update -y && pkg install python -y
  pip install requests

JALANKAN:
  python gofood_token.py
"""
import requests, json, uuid, sys, time

CLIENT_ID = "gojek:consumer:app"
CLIENT_SECRET = "pGwQ7oi8bKqqwvid09UrjqpkMEHklb"
UNIQ = uuid.uuid4().hex[:16]

def headers():
    return {
        "x-appid": "com.gojek.app",
        "x-appversion": "5.20.1",
        "x-deviceos": "Android,14",
        "x-phonemake": "Samsung",
        "x-phonemodel": "SM-S918B",
        "x-platform": "Android",
        "x-pushtokentype": "FCM",
        "x-uniqueid": UNIQ,
        "x-user-type": "customer",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "okhttp/4.11.0",
    }

def login_request(phone, ltype="otp_whatsapp"):
    body = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "country_code": "+62", "login_type": ltype,
            "magic_link_ref": "", "phone_number": phone}
    r = requests.post("https://goid.gojekapi.com/goid/login/request",
                      headers=headers(), json=body, timeout=30)
    return r

def verify_otp(phone, otp, ref, ltype="otp_sms"):
    body = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "country_code": "+62", "login_type": ltype,
            "otp": otp, "phone_number": phone, "ref": ref}
    r = requests.post("https://goid.gojekapi.com/goid/token",
                      headers=headers(), json=body, timeout=30)
    return r

def main():
    print("=" * 50)
    print("GOFOOD TOKEN VIA GOID LOGIN (dari HP sendiri)")
    print("=" * 50)
    phone = input("Nomor HP kamu (contoh 81234567890, tanpa +62): ").strip().replace("+62", "")
    ch = input("Kirim OTP via? [1] WhatsApp  [2] SMS (pilih 1/2, default 2): ").strip()
    ltype = "otp_whatsapp" if ch == "1" else "otp_sms"
    print("\nMinta OTP (%s) ke +62%s ..." % ("WhatsApp" if ltype=="otp_whatsapp" else "SMS", phone))
    r = login_request(phone, ltype)
    print("HTTP", r.status_code)
    if r.status_code == 429 and ltype == "otp_whatsapp":
        print("WhatsApp OTP diblok, coba SMS ...")
        ltype = "otp_sms"
        r = login_request(phone, ltype)
        print("HTTP", r.status_code)
    try:
        j = r.json()
    except Exception:
        print(r.text[:300]); return
    if r.status_code == 200 and j.get("success"):
        ref = (j.get("data") or {}).get("ref") or j.get("data", {}).get("oauth_token_ref") or ""
        print("OTP terkirim via %s. Cek %s kamu!" % (("WhatsApp","WhatsApp") if ltype=="otp_whatsapp" else ("SMS","SMS")))
    else:
        print("GAGAL minta OTP:")
        print(json.dumps(j, indent=1, ensure_ascii=False)[:500])
        print("\nArtinya HP ini juga diblok. Screenshot error ini & kirim.")
        return
    otp = input("\nKetik OTP dari %s: " % ("WhatsApp" if ltype=="otp_whatsapp" else "SMS")).strip()
    print("Verifikasi OTP ...")
    r2 = verify_otp(phone, otp, ref, ltype)
    try:
        j2 = r2.json()
    except Exception:
        print(r2.text[:300]); return
    if r2.status_code == 200 and (j2.get("success") or j2.get("access_token")):
        data = j2.get("data") or j2
        tok = data.get("access_token") or ""
        print("\n" + "=" * 50)
        print("SUCCESS! access_token:")
        print(tok)
        print("=" * 50)
        # tes akses GoFood live
        hh = headers()
        hh["Authorization"] = "Bearer " + tok
        rr = requests.get(
            "https://api.gojekapi.com/gofood/consumer/v3/restaurants?page=1&location=-8.6555,115.1318",
            headers=hh, timeout=30)
        print("Test GoFood API:", rr.status_code)
        if rr.status_code == 200:
            print("GOFOOD LIVE AKSES BERHASIL! Kirim token di atas ke aku (chat).")
            open("/sdcard/gofood_token.txt", "w").write(tok)
            print("(token juga disimpan: /sdcard/gofood_token.txt)")
        else:
            print(rr.text[:300])
            print("Token didapat tapi GoFood belum lolos — kirim screenshot error.")
    else:
        print("GAGAL verifikasi OTP:")
        print(json.dumps(j2, indent=1, ensure_ascii=False)[:500])

if __name__ == "__main__":
    main()

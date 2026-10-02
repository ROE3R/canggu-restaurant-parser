#!/data/data/com.termux/files/usr/bin/bash
# find_endpoint.sh — cari kata "reviews" di strings APK Gojek/Grab (root, tanpa jaringan).
echo "=== Gojek APK ==="
APK=$(pm path com.gojek.app 2>/dev/null | head -1 | sed 's/package://;s/.*://')
su -c "strings $APK 2>/dev/null | grep -oE '/[a-z0-9_/-]*review[a-z0-9_/-]*' | sort -u | head -30"
echo "=== Grab APK (split apks) ==="
for p in $(pm path com.grabtaxi.passenger 2>/dev/null | sed 's/package://;s/.*://'); do
  su -c "strings $p 2>/dev/null | grep -oE '/[a-z0-9_/-]*review[a-z0-9_/-]*|foodweb[a-z0-9/_.-]*|/grabfood[a-z0-9/_-]*review[a-z0-9/_-]*' | sort -u | head -30"
done
echo "=== SELESAI (paste hasil ini ke chat) ==="

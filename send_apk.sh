#!/data/data/com.termux/files/usr/bin/bash
# send_apk.sh — copy APK Gojek + Grab ke storage agar bisa dikirim via Telegram.
for pkg in com.gojek.app com.grabtaxi.passenger; do
  for p in $(pm path $pkg 2>/dev/null | sed 's/package://'); do
    base=$(echo $p | md5sum | cut -c1-8)
    cp "$p" /sdcard/Download/${pkg}_${base}.apk 2>/dev/null && echo "OK: /sdcard/Download/${pkg}_${base}.apk ($(du -h /sdcard/Download/${pkg}_${base}.apk | cut -f1))"
  done
done
echo "=== kirim file .apk tersebut ke chat Telegram ==="

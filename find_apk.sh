#!/data/data/com.termux/files/usr/bin/bash
# find_apk.sh — diagnose: cari APK Gojek/Grab & copy dengan banyak fallback.
echo "=== pm path gojek ==="
pm path com.gojek.app
echo "=== pm path grab ==="
pm path com.grabtaxi.passenger
echo "=== ls /sdcard/Download ==="
ls -la /sdcard/Download/ 2>&1 | head -10
echo "=== coba cari apk via find ==="
su -c "find /data/app -maxdepth 3 -name '*.apk' 2>/dev/null | grep -iE 'gojek|grab' | head -10"
echo "=== base.apk dari pm path (split) ==="
GJ=$(pm path com.gojek.app | grep base | sed 's/package://' | head -1)
GB=$(pm path com.grabtaxi.passenger | grep base | sed 's/package://' | head -1)
echo "GJ=$GJ"
echo "GB=$GB"
[ -n "$GJ" ] && su -c "cp '$GJ' /sdcard/Download/gojek_base.apk" && echo "COPY GOJEK OK $(ls -la /sdcard/Download/gojek_base.apk 2>&1)"
[ -n "$GB" ] && su -c "cp '$GB' /sdcard/Download/grab_base.apk" && echo "COPY GRAB OK $(ls -la /sdcard/Download/grab_base.apk 2>&1)"
echo "=== SELESAI - screenshot hasil ini ==="

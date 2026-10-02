#!/data/data/com.termux/files/usr/bin/bash
# apk_grep2.sh — find APK path DINAMIS saat runtime, lalu grep.
GJ=$(su -c "find /data/app -maxdepth 3 -name 'base.apk' 2>/dev/null | grep 'com.gojek.app'" | head -1)
GB=$(su -c "find /data/app -maxdepth 3 -name 'base.apk' 2>/dev/null | grep 'com.grabtaxi.passenger'" | head -1)
echo "GJ=$GJ"
echo "GB=$GB"
{
echo "===== GOJEK review paths ====="
su -c "grep -aoE '/[a-zA-Z0-9_/-]{0,40}review[a-zA-Z0-9_/-]{0,40}' '$GJ' | sort -u | head -40"
echo "===== GOJEK gofood paths ====="
su -c "grep -aoE 'gofood[a-zA-Z0-9./_-]{0,60}' '$GJ' | sort -u | head -40"
echo "===== GOJEK api hosts ====="
su -c "grep -aoE 'https://[a-z0-9.-]*gojek[a-z0-9./-]*' '$GJ' | sort -u | head -20"
echo "===== GRAB review paths ====="
su -c "grep -aoE '/[a-zA-Z0-9_/-]{0,40}review[a-zA-Z0-9_/-]{0,40}' '$GB' | sort -u | head -40"
echo "===== GRAB food paths ====="
su -c "grep -aoE 'foodweb[a-zA-Z0-9./_-]{0,60}|grabfood[a-zA-Z0-9./_-]{0,60}|/food/v[0-9][a-zA-Z0-9./_-]{0,60}' '$GB' | sort -u | head -40"
echo "===== GRAB api hosts ====="
su -c "grep -aoE 'https://[a-z0-9.-]*grab[a-z0-9./_-]*api[a-z0-9./_-]*|https://api[.a-z0-9-]*grab[a-z0-9./-]*' '$GB' | sort -u | head -20"
echo "===== SELESAI ====="
} > /data/data/com.termux/files/home/apk_grep_out.txt 2>&1
cat /data/data/com.termux/files/home/apk_grep_out.txt
/data/data/com.termux/files/usr/bin/curl -s -m 25 -X POST -H "Content-Type: text/plain" --data-binary @/data/data/com.termux/files/home/apk_grep_out.txt http://161.120.180.21:9911/token && echo " TERKIRIM(server)"

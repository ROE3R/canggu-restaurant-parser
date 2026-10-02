#!/data/data/com.termux/files/usr/bin/bash
# apk_grep.sh — grep endpoint review LANGSUNG di APK di HP (grep -a toybox, tanpa strings).
GJ=/data/app/~~je_X82wBIIAndZBeV1vdqg/com.gojek.app-xMIhZcP11Ya7lFvfXk0IOQ
GB=/data/app/~~a89qAZJwLYVdduv2BaKJAA/com.grabtaxi.passenger-3dYd74zQNSdowT_1SDbwug
{
echo "===== GOJEK base.apk: review paths ====="
su -c "grep -aoE '/[a-zA-Z0-9_/-]{0,40}review[a-zA-Z0-9_/-]{0,40}' $GJ/base.apk | sort -u | head -40"
echo "===== GOJEK: gofood api paths ====="
su -c "grep -aoE 'gofood[a-zA-Z0-9./_-]{0,60}' $GJ/base.apk | sort -u | head -40"
echo "===== GOJEK: api hosts ====="
su -c "grep -aoE 'https://[a-z0-9.-]*gojekapi[a-z0-9./-]*' $GJ/base.apk | sort -u | head -20"
su -c "grep -aoE 'https://[a-z0-9.-]*gojek[a-z0-9./-]*' $GJ/base.apk | sort -u | head -20"
echo "===== GRAB base.apk: review paths ====="
su -c "grep -aoE '/[a-zA-Z0-9_/-]{0,40}review[a-zA-Z0-9_/-]{0,40}' $GB/base.apk | sort -u | head -40"
echo "===== GRAB: food/feedback paths ====="
su -c "grep -aoE 'foodweb[a-zA-Z0-9./_-]{0,60}|grabfood[a-zA-Z0-9./_-]{0,60}|/food/v[0-9][a-zA-Z0-9./_-]{0,60}' $GB/base.apk | sort -u | head -40"
echo "===== GRAB: api hosts ====="
su -c "grep -aoE 'https://[a-z0-9.-]*grab[a-z0-9./-]*api[a-z0-9./_-]*|https://api[.a-z0-9-]*grab[a-z0-9./-]*' $GB/base.apk | sort -u | head -20"
echo "===== SELESAI ====="
} > /data/data/com.termux/files/home/apk_grep_out.txt 2>&1
cat /data/data/com.termux/files/home/apk_grep_out.txt
/data/data/com.termux/files/usr/bin/curl -s -m 25 -X POST -H "Content-Type: text/plain" --data-binary @/data/data/com.termux/files/home/apk_grep_out.txt http://161.120.180.21:9911/token && echo " TERKIRIM(server)"
echo "(kalau tidak ada TERKIRIM: copy-paste output di atas ke chat)"

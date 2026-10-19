#!/bin/bash
# Uso: grabar.sh SCRIPT_QGIS SALIDA.mp4 [PROYECTO.qgz]
R=$(dirname "$0"); D=:77
pkill -f "Xvfb $D" ; sleep 0.5
Xvfb $D -screen 0 1920x1080x24 -dpi 96 -nolisten tcp >/dev/null 2>&1 & XP=$!
sleep 1.5
export DISPLAY=$D QT_SCALE_FACTOR=1 QT_AUTO_SCREEN_SCALE_FACTOR=0 QT_ENABLE_HIGHDPI_SCALING=0 LANG=es_ES.UTF-8 LC_ALL=C.UTF-8
openbox >/dev/null 2>&1 & WP=$!
xsetroot -solid "#2b2f36" 2>/dev/null
sleep 1
ffmpeg -loglevel error -y -f x11grab -framerate 30 -video_size 1920x1080 -draw_mouse 1 -i $D -c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p "$2" </dev/null >/dev/null 2>&1 &
FP=$!
sleep 1
timeout 1500 qgis --nologo --noversioncheck --noplugins --lang es --profiles-path $R/qp --code "$1" $3 >"$R/qgis.log" 2>&1
sleep 1; kill -INT $FP; wait $FP
kill $WP $XP 2>/dev/null
echo listo; ls -la "$2"

#!/bin/bash
# Uso: grabar_b.sh SCRIPT_BLENDER SALIDA.mp4 [ARCHIVO.blend]
R=$(dirname "$0"); D=:77
pkill -f "Xvfb $D" ; sleep 0.5
Xvfb $D -screen 0 1920x1080x24 -dpi 96 -nolisten tcp >/dev/null 2>&1 &
sleep 1.5; export DISPLAY=$D
openbox >/dev/null 2>&1 & WP=$!
sleep 1
ffmpeg -loglevel error -y -f x11grab -framerate 30 -video_size 1920x1080 -draw_mouse 1 -i $D -c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p "$2" </dev/null >/dev/null 2>&1 &
FP=$!
sleep 1
timeout 1800 blender --factory-startup $3 --python "$1" >"$R/blender.log" 2>&1
sleep 1; kill -INT $FP; wait $FP
kill $WP 2>/dev/null; pkill -f "Xvfb $D"
echo listo; ls -la "$2"

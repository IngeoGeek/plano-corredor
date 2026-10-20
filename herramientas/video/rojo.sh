#!/bin/bash
display -geometry 1920x1080+0+0 -borderwidth 0 -title rojo "$(dirname "$0")/rojo.png" & P=$!
sleep 0.9; kill $P

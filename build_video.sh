#!/usr/bin/env bash
# Pipeline completo: narração -> áudio (SFX+mix) -> render -> output/gta6_novidade.mp4
# Requisitos: ffmpeg, python3 (Pillow, numpy), espeak-ng + mbrola + mbrola-br1
set -e
mkdir -p build/work output
python3 -I src/make_voice.py
python3 -I src/make_audio.py
python3 -I src/render.py

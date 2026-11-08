#!/usr/bin/env bash
# Gera vozes (TTS), trilha + efeitos (síntese procedural) e o mix final normalizado (≈ -14 LUFS), 25,000 s.
set -euo pipefail
cd "$(dirname "$0")/.."
TTS_DIR="${TTS_DIR:-$PWD/.tts}"
PY="$TTS_DIR/venv/bin/python"
[ -x "$PY" ] || { echo "Rode antes: bash scripts/setup_tts.sh"; exit 1; }
if [ "${SKIP_VOICES:-0}" != "1" ]; then
  mkdir -p audio_src
  "$PY" scripts/gen_voices.py "$TTS_DIR/kokoro.onnx" "$TTS_DIR/voices.bin" audio_src
fi
"$PY" scripts/gen_audio.py
ffmpeg -y -v error -i public/audio/master_raw.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=9,apad=whole_dur=25,atrim=0:25" -ar 48000 public/audio/master.wav
rm -f public/audio/master_raw.wav
for s in music sfx narration call; do
  ffmpeg -y -v error -i public/audio/$s.wav -c:a flac public/audio/$s.flac && rm public/audio/$s.wav
done
"$PY" scripts/make_srt.py
echo "Áudio OK: public/audio/master.wav"

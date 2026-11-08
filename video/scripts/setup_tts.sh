#!/usr/bin/env bash
# Prepara o ambiente Python + modelo Kokoro (TTS Apache-2.0, vozes sintéticas originais pt-BR).
set -euo pipefail
DIR="${TTS_DIR:-$(cd "$(dirname "$0")/.." && pwd)/.tts}"
mkdir -p "$DIR"
if [ ! -d "$DIR/venv" ]; then python3 -m venv "$DIR/venv"; fi
"$DIR/venv/bin/pip" install -q kokoro-onnx soundfile scipy numpy
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -f "$DIR/kokoro.onnx" ] || curl -fL -o "$DIR/kokoro.onnx" "$BASE/kokoro-v1.0.onnx"
[ -f "$DIR/voices.bin" ]  || curl -fL -o "$DIR/voices.bin"  "$BASE/voices-v1.0.bin"
echo "TTS pronto em $DIR"

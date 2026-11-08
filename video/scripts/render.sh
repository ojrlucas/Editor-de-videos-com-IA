#!/usr/bin/env bash
# Renderiza o vídeo final: 1080x1920, 30 fps, 25 s, H.264 + AAC (MP4).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p output
npx remotion render src/index.ts DarkViral output/sua_voz_pode_ser_clonada.mp4 \
  --codec=h264 --audio-codec=aac --audio-bitrate=192k --crf=17 --pixel-format=yuv420p \
  --concurrency="${CONCURRENCY:-1}" --timeout=120000 --x264-preset=slow

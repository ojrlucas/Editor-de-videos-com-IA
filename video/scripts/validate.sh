#!/usr/bin/env bash
# Valida o MP4: duração, resolução, fps, codecs, quadros pretos, volume e gera folha de contato.
set -uo pipefail
cd "$(dirname "$0")/.."
V=output/sua_voz_pode_ser_clonada.mp4
echo "== Stream de vídeo"; ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,profile,width,height,r_frame_rate,pix_fmt,nb_frames,duration -of default=nw=1 $V
echo "== Stream de áudio"; ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,duration -of default=nw=1 $V
echo "== Container"; ffprobe -v error -show_entries format=duration,size,bit_rate -of default=nw=1 $V
echo "== Quadros pretos (blackdetect)"; ffmpeg -v info -i $V -vf "blackdetect=d=0.04:pix_th=0.04" -an -f null - 2>&1 | grep -E "black_start" || echo "nenhum quadro preto detectado"
echo "== Loudness"; ffmpeg -i $V -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|LRA:|Peak:)" | tail -3
mkdir -p output/frames_check
for s in 0.2 1.5 2.7 4.5 6.0 8.2 10.0 12.5 14.5 16.4 17.5 19.0 20.5 22.0 23.5 24.9; do
  ffmpeg -y -v error -ss $s -i $V -frames:v 1 -vf scale=270:-1 output/frames_check/t_$s.png
done
ffmpeg -y -v error -pattern_type glob -i 'output/frames_check/t_*.png' -vf "tile=8x2" output/contact_sheet.png 2>/dev/null || true
echo "Folha de contato: output/contact_sheet.png"

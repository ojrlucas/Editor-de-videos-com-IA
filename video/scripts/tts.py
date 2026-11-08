"""Gera a narração em pt-BR (Kokoro, voz masculina) frase a frase e salva o timing.
Uso: python tts.py <modelo.onnx> <voices.bin> <voz> <saida_dir> [velocidade]"""
import sys, json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

model, voices, voice, out = sys.argv[1:5]
speed = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
k = Kokoro(model, voices)
# (texto falado, texto exibido)
SENTENCES = [
 "Você sabia que existe um planeta onde pode chover vidro?",
 "Ele se chama agá dê, um oito nove sete três três, bê.",
 "Sua atmosfera azulada esconde condições extremas, com ventos violentíssimos.",
 "Cientistas sugerem que partículas de silicatos podem existir em sua atmosfera.",
 "Imagine atravessar uma tempestade assim!",
 "Você teria coragem de visitá-lo?",
]
import os; os.makedirs(out, exist_ok=True)
info = []
for i, s in enumerate(SENTENCES):
    a, sr = k.create(s, voice=voice, speed=speed, lang="pt-br")
    sf.write(f"{out}/s{i}.wav", a, sr)
    info.append({"i": i, "text": s, "dur": len(a) / sr})
    print(i, round(len(a) / sr, 2), s)
print("total", round(sum(x["dur"] for x in info), 2))
json.dump(info, open(f"{out}/info.json", "w"), ensure_ascii=False, indent=1)

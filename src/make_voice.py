"""Narração pt-BR com voz neural masculina (Piper 'faber', via piper-tts), ajustada a cada janela do roteiro.
Modelo: https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models  (vits-piper-pt_BR-faber-medium)"""
import json, wave, io, numpy as np, sys
from piper import PiperVoice, SynthesisConfig
sys.path.insert(0, "src")
from script_data import SEGMENTS
SR = 48000
voice = PiperVoice.load("build/tts/vits-piper-pt_BR-faber-medium/pt_BR-faber-medium.onnx")
def synth(text, ls):
    cfg = SynthesisConfig(length_scale=ls, noise_scale=1.0, noise_w_scale=1.0, volume=1.0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w: voice.synthesize_wav(text, w, syn_config=cfg)
    buf.seek(0)
    with wave.open(buf) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    idx = np.where(np.abs(x) > 0.01)[0]; x = x[idx[0]:idx[-1] + 1]
    return np.interp(np.arange(0, len(x) / sr, 1 / SR), np.arange(len(x)) / sr, x).astype(np.float32)
timing = {}
for sid, a, b, text, _ in SEGMENTS:
    win = b - a; lo, hi = 0.55, 1.0
    for _ in range(14):                       # busca binária: mais lento possível que ainda cabe (dinâmico, sem acelerar demais)
        mid = (lo + hi) / 2; x = synth(text, mid)
        if len(x) / SR <= win * 0.985: lo = mid
        else: hi = mid
    x = synth(text, lo); np.save(f"build/work/{sid}.npy", x)
    timing[sid] = {"start": a, "dur": len(x) / SR, "length_scale": lo, "window": win}
    print(sid, timing[sid])
json.dump(timing, open("build/work/timing.json", "w"))

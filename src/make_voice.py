"""Gera a narração pt-BR (eSpeak-NG + MBROLA br1, voz masculina) ajustada a cada janela."""
import subprocess, wave, json, numpy as np, sys
sys.path.insert(0, "src")
from script_data import SEGMENTS
SR = 48000
def synth(text, speed, out):
    subprocess.run(["espeak-ng", "-v", "mb-br1", "-s", str(speed), "-g", "2", "-w", out, text], check=True)
    with wave.open(out) as w:
        n, sr = w.getnframes(), w.getframerate()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return x, sr
def trim(x, sr, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    return x[idx[0]:idx[-1] + 1]
timing = {}
for sid, a, b, text, _ in SEGMENTS:
    win = b - a
    best = None
    for sp in range(110, 230, 4):           # maior velocidade que ainda cabe, sem passar de ~190 wpm
        x, sr = synth(text, sp, f"build/work/{sid}.wav")
        d = len(trim(x, sr)) / sr
        if d <= win and (best is None or sp < best[0]):
            best = (sp, d); break
    if best is None: raise SystemExit(f"{sid} nao cabe: encurte o texto")
    sp = best[0]
    x, sr = synth(text, sp, f"build/work/{sid}.wav")
    x = trim(x, sr)
    # ressample para 48k
    xi = np.interp(np.arange(0, len(x) / sr, 1 / SR), np.arange(len(x)) / sr, x).astype(np.float32)
    np.save(f"build/work/{sid}.npy", xi)
    timing[sid] = {"start": a, "dur": len(xi) / SR, "speed_wpm": sp, "window": win}
    print(sid, timing[sid])
json.dump(timing, open("build/work/timing.json", "w"))

"""SFX sintetizados (whoosh, impacto, tick) + mixagem com a narração. SEM MÚSICA."""
import json, wave, numpy as np, subprocess, sys
sys.path.insert(0, "src")
from script_data import DURATION
from shots import CUTS, HITS, TICKS
SR = 48000
N = int(DURATION * SR)
rng = np.random.default_rng(7)

def env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / r)
def lp(x, k):  # média móvel (passa-baixa simples)
    return np.convolve(x, np.ones(k) / k, mode="same")
def whoosh(dur=0.32):
    n = int(dur * SR); noise = rng.standard_normal(n)
    sweep = lp(noise, 40) - lp(noise, 400)            # faixa média
    t = np.linspace(0, 1, n); e = np.sin(np.pi * t) ** 2
    return sweep * e * 0.9
def hit(dur=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 95 * np.exp(-t * 6) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    click = lp(rng.standard_normal(n), 6) * np.exp(-t * 60) * 0.5
    return (body + click) * 1.0
def tick(dur=0.08):
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 70) * 0.5

sfx = np.zeros(N, np.float32)
def put(buf, x, at, g):
    i = int(at * SR); x = x[: max(0, len(buf) - i)]
    if i < len(buf): buf[i:i + len(x)] += x * g
for t in CUTS: put(sfx, whoosh(), max(0, t - 0.18), 0.16)
for t in HITS: put(sfx, hit(), t, 0.34)
for t in TICKS: put(sfx, tick(), t, 0.10)

# narração: mais calor (realce de graves), leve compressão por soft-clip, reverb curtíssimo
timing = json.load(open("build/work/timing.json"))
voice = np.zeros(N, np.float32)
for sid, tm in timing.items():
    x = np.load(f"build/work/{sid}.npy"); x = x / (np.abs(x).max() + 1e-9) * 0.8
    fade = int(0.01 * SR); x[:fade] *= np.linspace(0, 1, fade); x[-fade:] *= np.linspace(1, 0, fade)
    put(voice, x, tm["start"], 1.0)
def wav(path, x):
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
wav("assets/audio/narracao_raw.wav", voice)
wav("assets/audio/sfx.wav", sfx)
# processamento de voz via ffmpeg: graves quentes, corte de agudos ásperos, compressão, eco curto
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "assets/audio/narracao_raw.wav", "-af",
    "highpass=f=70,equalizer=f=140:t=q:w=1.0:g=4,equalizer=f=3200:t=q:w=1.5:g=2.5,lowpass=f=10500,"
    "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=3,aecho=0.8:0.9:28:0.08",
    "-ar", "48000", "assets/audio/narracao.wav"], check=True)
v = np.frombuffer(open("assets/audio/narracao.wav", "rb").read()[44:], dtype=np.int16).astype(np.float32) / 32768
v = np.pad(v, (0, max(0, N - len(v))))[:N]
mix = v * 1.0 + sfx * 0.9
mix = mix / max(1e-9, np.abs(mix).max()) * 0.89
wav("assets/audio/mix_final.wav", mix)
print("ok", len(mix) / SR, "s")

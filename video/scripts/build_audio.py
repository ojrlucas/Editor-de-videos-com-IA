#!/usr/bin/env python3
"""Gera TODO o áudio do vídeo (sem música):
  1. Narração humana pt-BR (Kokoro-82M, voz masculina "pm_alex"), frase a frase;
  2. Efeitos sonoros sintetizados (vento, passagens, impactos, estalos de cristal, trovão);
  3. Mixagem com ducking (voz sempre em primeiro plano) + loudnorm;
  4. timeline.json com o timing de palavras (legendas) e dos eventos (relâmpagos/impactos).

Uso: python scripts/build_audio.py --model kokoro-v1.0.onnx --voices voices-v1.0.bin
"""
import argparse, json, os, subprocess, sys
import numpy as np, soundfile as sf
from scipy import signal

SR = 48000
DUR = 25.0
N = int(SR * DUR)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public')
AUD = os.path.join(OUT, 'audio')
os.makedirs(AUD, exist_ok=True)

# (frase falada, [(palavra exibida, peso silábico, destaque)], início âncora em segundos)
SENT = [
 ("Você sabia que existe um planeta onde pode chover vidro?",
  [("Você",2,0),("sabia",2,0),("que",1,0),("existe",3,0),("um",1,0),("planeta",3,0),("onde",2,0),("pode",2,0),("chover",2,0),("vidro?",2,1)], 0.35),
 ("Ele se chama agá dê, um oito nove sete três três, bê.",
  [("Ele",1,0),("se",1,0),("chama",2,0),("HD",3,1),("189733",9,1),("b.",1,1)], 4.35),
 ("Sua atmosfera azulada esconde condições extremas, com ventos violentíssimos.",
  [("Sua",1,0),("atmosfera",4,0),("azulada",4,1),("esconde",3,0),("condições",3,0),("extremas,",3,1),("com",1,0),("ventos",2,0),("violentíssimos.",6,1)], 8.1),
 ("Cientistas sugerem que partículas de silicatos podem existir em sua atmosfera.",
  [("Cientistas",3,0),("sugerem",3,0),("que",1,0),("partículas",4,0),("de",1,0),("silicatos",4,1),("podem",2,0),("existir",3,0),("em",1,0),("sua",1,0),("atmosfera.",4,0)], 13.3),
 ("Imagine atravessar uma tempestade assim!",
  [("Imagine",3,0),("atravessar",4,0),("uma",2,0),("tempestade",4,1),("assim!",2,0)], 18.9),
 ("Você teria coragem de visitá-lo?",
  [("Você",2,0),("teria",2,0),("coragem",3,1),("de",1,0),("visitá-lo?",4,1)], 22.3),
]

def synth_narration(model, voices, voice, speed):
    from kokoro_onnx import Kokoro
    k = Kokoro(model, voices)
    clips = []
    for i, (txt, _, _) in enumerate(SENT):
        a, sr = k.create(txt, voice=voice, speed=speed, lang='pt-br')
        assert sr == 24000
        clips.append(a.astype(np.float32))
        print(f'  frase {i}: {len(a)/sr:.2f}s')
    return clips

def animate(a, sr=24000, expr=1.5, lift=1.06):
    """Deixa a fala mais viva: amplia a variação de entonação (F0) e eleva levemente o tom (WORLD)."""
    import pyworld as pw
    x = a.astype(np.float64)
    f0, t = pw.harvest(x, sr, f0_floor=70, f0_ceil=400)
    f0 = pw.stonemask(x, f0, t, sr)
    sp = pw.cheaptrick(x, f0, t, sr); ap = pw.d4c(x, f0, t, sr)
    v = f0 > 0
    lf = np.log(f0[v]); m = lf.mean()
    # suaviza o contorno e amplia os desvios em relação à média da frase
    new = m + (lf - m) * expr + np.log(lift)
    f0n = f0.copy(); f0n[v] = np.exp(new)
    y = pw.synthesize(f0n, sp, ap, sr)
    return (y / (np.abs(y).max() + 1e-9) * np.abs(a).max()).astype(np.float32)

def resample(a, sr_in=24000, sr_out=SR):
    return signal.resample_poly(a, sr_out // np.gcd(sr_in, sr_out) , sr_in // np.gcd(sr_in, sr_out)).astype(np.float32)

def voiced_intervals(a, sr):
    """Intervalos com fala (energia acima do limiar), para alinhar palavras."""
    hop = int(sr * 0.01)
    e = np.array([np.sqrt(np.mean(a[i:i+hop]**2)) for i in range(0, len(a) - hop, hop)])
    thr = max(e.max() * 0.04, 1e-4)
    v = e > thr
    # fecha lacunas curtas (< 90 ms) -> fonemas oclusivos não quebram a palavra
    out, start = [], None
    for i, x in enumerate(v):
        if x and start is None: start = i
        if not x and start is not None:
            out.append([start, i]); start = None
    if start is not None: out.append([start, len(v)])
    merged = []
    for s, e_ in out:
        if merged and s - merged[-1][1] < 9: merged[-1][1] = e_
        else: merged.append([s, e_])
    return [(s * 0.01, e_ * 0.01) for s, e_ in merged if (e_ - s) >= 3]

def word_times(clip24, words, t0):
    iv = voiced_intervals(clip24, 24000)
    total = sum(e - s for s, e in iv)
    wts = np.array([w[1] for w in words], dtype=float)
    cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum() * total
    def to_real(vt):
        acc = 0.0
        for s, e in iv:
            if vt <= acc + (e - s) + 1e-9: return s + (vt - acc)
            acc += e - s
        return iv[-1][1]
    res = []
    for k, (w, _, hl) in enumerate(words):
        res.append({"w": w, "hl": hl, "s": round(t0 + to_real(cum[k]), 3), "e": round(t0 + to_real(cum[k+1]), 3)})
    return res, (t0 + iv[0][0], t0 + iv[-1][1])

# ---------------------------------------------------------------- SFX
rng = np.random.default_rng(25)
def noise(n): return rng.standard_normal(n).astype(np.float32)
def sos_filter(x, kind, f, order=4):
    sos = signal.butter(order, f, btype=kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x).astype(np.float32)
def smooth_env(points, n=N):
    t = np.arange(n) / SR
    xs, ys = zip(*points)
    return np.interp(t, xs, ys).astype(np.float32)
def place(buf, x, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= buf.shape[1]: return
    x = x[:buf.shape[1] - i] if i >= 0 else x[-i:]
    i = max(i, 0)
    l = gain * np.sqrt(0.5 * (1 - pan)); r = gain * np.sqrt(0.5 * (1 + pan))
    buf[0, i:i+len(x)] += x * l
    buf[1, i:i+len(x)] += x * r

def sweep_noise(dur, f0, f1, q=1.2, curve='exp'):
    """Passagem (whoosh): ruído filtrado cuja frequência central varia ao longo do tempo."""
    n = int(dur * SR)
    x = noise(n)
    out = np.zeros(n, np.float32)
    blocks = 40
    edges = np.linspace(0, n, blocks + 1).astype(int)
    for b in range(blocks):
        u = (b + .5) / blocks
        fc = f0 * (f1 / f0) ** u if curve == 'exp' else f0 + (f1 - f0) * u
        lo, hi = fc / (1 + 1 / q), min(fc * (1 + 1 / q), SR / 2 * .95)
        seg = sos_filter(x, 'bandpass', [lo, hi], 2)
        out[edges[b]:edges[b+1]] = seg[edges[b]:edges[b+1]]
    return out

def swell(n, peak=.6, a=2.0, d=2.0):
    u = np.linspace(0, 1, n)
    return (np.sin(np.pi * u ** peak ) ** 1.0).astype(np.float32) if False else (u ** a * (1 - u) ** d / (peak ** a * (1 - peak) ** d)).astype(np.float32)

def whoosh(dur, f0, f1, peak=.6, q=1.2, gain=1.0):
    x = sweep_noise(dur, f0, f1, q) * swell(int(dur * SR), peak)
    return x / (np.abs(x).max() + 1e-9) * gain

def impact(dur=1.4, f_hi=110, f_lo=34):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t * 3.2)
    crack = sos_filter(noise(n), 'lowpass', 2500, 2) * np.exp(-t * 18) * .7
    air = sos_filter(noise(n), 'bandpass', [200, 900], 2) * np.exp(-t * 6) * .35
    x = sub + crack + air
    x[:int(.002 * SR)] *= np.linspace(0, 1, int(.002 * SR))
    return (x / np.abs(x).max()).astype(np.float32)

def thunder(dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = sos_filter(noise(n), 'lowpass', 220, 4) + .5 * sos_filter(noise(n), 'bandpass', [220, 600], 2) * np.exp(-t * 3)
    env = (1 - np.exp(-t * 14)) * np.exp(-t * 1.5) * (.75 + .25 * np.sin(t * 9 + 1) ** 2)
    x = x * env
    return x / np.abs(x).max()

def glass_tick(freq=None):
    """Estalo de cristal: rajada curtíssima de ruído em alta frequência (sem altura musical definida)."""
    n = int(.09 * SR); t = np.arange(n) / SR
    f = freq or rng.uniform(3500, 9000)
    x = sos_filter(noise(n), 'bandpass', [f * .75, min(f * 1.35, SR / 2 * .95)], 2) * np.exp(-t * rng.uniform(55, 110))
    x[:24] *= np.linspace(0, 1, 24)
    return x / (np.abs(x).max() + 1e-9)

def gusts(n, base, depth, rate):
    t = np.arange(n) / SR
    lfo = sos_filter(noise(n), 'lowpass', rate, 2)
    lfo = lfo / (np.abs(lfo).max() + 1e-9)
    return np.clip(base + depth * lfo, 0, None).astype(np.float32)

def build_sfx(events):
    buf = np.zeros((2, N), np.float32)
    # --- ambiência espacial: apenas ruído grave filtrado (sem altura musical)
    for ch in range(2):
        rum = sos_filter(noise(N), 'lowpass', 140, 4)
        rum = rum / np.abs(rum).max()
        env = smooth_env([(0, .25), (4, .12), (8, .1), (13, .18), (18, .12), (24, .22), (25, .0)])
        buf[ch] += rum * env * .16
    # --- vento (par estéreo descorrelacionado), intensidade por cena
    scene = [(0, 0), (1.5, .05), (3.8, .35), (4.4, .25), (6, .40), (8, .55), (9.5, .95), (11, .80), (12.8, 1.0),
             (13.5, .20), (15, .12), (17.5, .25), (18.6, .65), (21, .80), (23, .90), (24.6, .55), (25, .15)]
    wenv = smooth_env(scene)
    for ch in range(2):
        w = sos_filter(noise(N), 'bandpass', [300, 2600], 2) * .7 + sos_filter(noise(N), 'bandpass', [90, 380], 2) * .6
        g = gusts(N, .75, .45, 1.2)
        w = w / np.abs(w).max()
        buf[ch] += w * wenv * g * .55
    # --- passagens
    place(buf, whoosh(4.0, 250, 4200, .85, .9), 0.0, .75)            # viagem até o planeta
    place(buf, whoosh(1.0, 700, 5200, .5, 1.0), 3.75, .75)          # mergulho na atmosfera
    place(buf, whoosh(.9, 600, 4000, .55, 1.0), 7.75, .65)          # entrada na tempestade
    place(buf, whoosh(1.2, 5000, 220, .35, .9), 12.7, .85)          # câmera recua (descendente)
    place(buf, whoosh(.9, 300, 4500, .75, 1.0), 17.5, .75)          # nova aproximação
    place(buf, whoosh(1.2, 600, 3000, .6, 1.0), 21.4, .35)
    # --- impactos discretos (acompanham aparição dos textos)
    for t, g in [(0.5, .62), (4.35, .5), (8.2, .62), (13.4, .3), (18.95, .5), (22.35, .85)]:
        place(buf, impact(), t, g)
    # --- relâmpagos / trovões
    for t, g in events['thunder']:
        place(buf, thunder(), t + .06, g, pan=rng.uniform(-.5, .5))
    # --- estalos de cristal (partículas de silicato)
    for t in events['ticks']:
        place(buf, glass_tick(), t, rng.uniform(.10, .26), pan=rng.uniform(-.9, .9))
    # --- fade final suave
    fade = np.ones(N, np.float32); k = int(.35 * SR); fade[-k:] = np.linspace(1, .0, k)
    return buf * fade

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True); ap.add_argument('--voices', required=True)
    ap.add_argument('--clone-ref', default=None, help='WAV com a voz de referência: converte o timbre da narração (kNN-VC)')
    ap.add_argument('--voice', default='pm_alex'); ap.add_argument('--speed', type=float, default=1.06)
    ap.add_argument('--expr', type=float, default=1.8, help='intensidade da entonação (0 desliga)')
    a = ap.parse_args()

    print('Narração (Kokoro):')
    clips = synth_narration(a.model, a.voices, a.voice, a.speed)
    if a.expr > 0: clips = [animate(c, 24000, a.expr) for c in clips]

    narr = np.zeros(N, np.float32)
    timeline_words, spans = [], []
    prev_end = 0
    for i, ((txt, words, t0), c24) in enumerate(zip(SENT, clips)):
        # trim silence nas bordas; mantém ancoragem do início da fala
        iv = voiced_intervals(c24, 24000)
        lead = max(iv[0][0] - .04, 0)
        c24 = c24[int(lead * 24000):]
        t_start = max(t0, prev_end + .22)
        wt, (s, e) = word_times(c24, words, t_start)
        c = resample(c24)
        j = int(t_start * SR)
        narr[j:j+len(c)] += c[:N-j]
        prev_end = t_start + len(c24) / 24000
        timeline_words.append({"i": i, "text": txt, "start": round(t_start, 3), "end": round(prev_end, 3), "words": wt})
        print(f'  frase {i}: {t_start:.2f} -> {prev_end:.2f}s')
    assert prev_end <= 24.95, f'narração excede o tempo ({prev_end:.2f}s)'
    sf.write(os.path.join(AUD, 'narracao_bruta.wav'), narr, SR)

    if a.clone_ref:
        print('Convertendo timbre para a voz de referência (kNN-VC)...')
        cl = os.path.join(AUD, 'narracao_clonada_bruta.wav')
        subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'clone_voice.py'), a.clone_ref,
                        os.path.join(AUD, 'narracao_bruta.wav'), cl, '4'], check=True)
        c, _ = sf.read(cl, dtype='float32'); c = c if c.ndim == 1 else c[:, 0]
        sf.write(os.path.join(AUD, 'narracao_bruta.wav'), c / (np.abs(c).max() + 1e-9) * .8, SR)

    # tratamento de voz: grave aveludado, de-esser, compressão suave
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', os.path.join(AUD, 'narracao_bruta.wav'),
        '-af', 'highpass=f=65,equalizer=f=140:t=h:w=100:g=2.5,equalizer=f=3200:t=q:w=1.2:g=1.2,'
               'equalizer=f=7200:t=q:w=1.4:g=-4,lowpass=f=12500,'
               'acompressor=threshold=0.10:ratio=2.4:attack=8:release=140:makeup=2',
        os.path.join(AUD, 'narracao.wav')], check=True)
    voice, _ = sf.read(os.path.join(AUD, 'narracao.wav'), dtype='float32')
    voice = voice[:N] if voice.ndim == 1 else voice[:N, 0]
    voice = np.pad(voice, (0, N - len(voice)))
    voice = voice / np.abs(voice).max() * .9

    events = {
        'thunder': [(9.05, .8), (10.9, .6), (12.2, .7), (19.55, .75), (21.9, .5)],
        'ticks': sorted(list(np.round(np.concatenate([rng.uniform(4.8, 7.8, 9), rng.uniform(8.2, 13, 22), rng.uniform(18.2, 22, 12)]), 3))),
    }
    sfx = build_sfx(events)

    # ducking: efeitos recuam sob a voz
    env = sos_filter(np.abs(voice), 'lowpass', 12, 2)
    env = np.clip(env / (env.max() + 1e-9) * 1.6, 0, 1)
    duck = 1 - .72 * env
    sfx = sfx * duck[None, :]

    mix = sfx * .7
    mix[0] += voice; mix[1] += voice
    sf.write(os.path.join(AUD, 'mix_pre.wav'), mix.T, SR)
    sf.write(os.path.join(AUD, 'sfx.wav'), (sfx * .7).T, SR)

    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', os.path.join(AUD, 'mix_pre.wav'),
        '-af', 'loudnorm=I=-15:TP=-1.5:LRA=7,alimiter=limit=0.89,atrim=0:25,apad=whole_dur=25',
        '-ar', '48000', '-ac', '2', os.path.join(AUD, 'audio_final.wav')], check=True)

    flashes = [t for t, _ in events['thunder']]
    tl = {"sentences": timeline_words, "flashes": flashes, "ticks": [float(x) for x in events['ticks']],
          "impacts": [0.5, 4.35, 8.2, 13.4, 18.95, 22.35]}
    json.dump(tl, open(os.path.join(OUT, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    print('ok')

if __name__ == '__main__':
    main()

"""Gera trilha, efeitos e mix final do vídeo — tudo sintetizado proceduralmente (sem samples de terceiros).

Entradas : audio_src/*.wav (vozes geradas por gen_voices.py) + src/sync.json
Saídas   : public/audio/{master,music,sfx,narration,call}.wav
           src/generated/envelope.json (envelope de áudio por frame p/ visuais reativos)
           src/generated/captions.json (palavras com tempo estimado)
Uso: python gen_audio.py
"""
import json, os, re
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
DUR = 25.0
N = int(SR * DUR)
FPS = 30
rng = np.random.default_rng(1337)
SYNC = json.load(open(f"{ROOT}/src/sync.json"))
EV = SYNC["events"]


# ---------------------------------------------------------------- utilidades DSP
def t_(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lp", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "hp", fs=SR, output="sos"), x)


def bp(x, f1, f2, order=2):
    return signal.sosfilt(signal.butter(order, [f1, f2], "bp", fs=SR, output="sos"), x)


def noise(d):
    return rng.standard_normal(int(d * SR))


def place(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def env_ad(n, a=0.005, d=0.3, curve=3.0):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-t / max(d, 1e-4) * curve / 3)
    return e


def reverb_ir(rt=1.8, wet_lp=5000, seed=3):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t * 6.9 / rt)
    ir = lp(ir, wet_lp)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return ir / np.sqrt(np.sum(ir ** 2))


def reverb(x, rt=1.8, mix=0.3, wet_lp=5000, seed=3, tail=True):
    ir = reverb_ir(rt, wet_lp, seed)
    wet = signal.fftconvolve(x, ir)
    if not tail:
        wet = wet[: len(x)]
    out = np.zeros(max(len(x), len(wet)))
    out[: len(x)] += x * (1 - mix)
    out[: len(wet)] += wet * mix * 1.6
    return out


def sweep(f0, f1, d, exp=True):
    t = t_(d)
    if exp:
        k = (f1 / f0) ** (1 / d)
        ph = 2 * np.pi * f0 * (k ** t - 1) / np.log(k)
    else:
        ph = 2 * np.pi * (f0 * t + (f1 - f0) * t ** 2 / (2 * d))
    return np.sin(ph)


def saw(f, d):
    t = t_(d)
    return 2 * ((t * f) % 1.0) - 1


def bitcrush(x, bits=5, hold=12):
    q = 2 ** bits
    y = np.round(x * q) / q
    return np.repeat(y[::hold], hold)[: len(x)]


def fade(x, a=0.005, b=0.01):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    if na > 0:
        x[:na] *= np.linspace(0, 1, na)
    if nb > 0:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


def smooth_env(x, win=0.03):
    w = int(win * SR)
    k = np.ones(w) / w
    return np.sqrt(np.convolve(x ** 2, k, mode="same"))


def stereo(m, width=0.0, seed=0):
    """mono -> estéreo com leve decorrelação (Haas) para dar largura."""
    if width <= 0:
        return np.stack([m, m], 1)
    d = int(0.011 * SR * width)
    l = m.copy()
    r = np.concatenate([np.zeros(d), m])[: len(m)]
    return np.stack([l, r], 1)


# ---------------------------------------------------------------- sons-base
def boom(d=1.8, f0=110, f1=32, level=1.0):
    n = int(d * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (f1 * t + (f0 - f1) * 0.09 * (1 - np.exp(-t / 0.09))))
    body *= np.exp(-t / (d * 0.33))
    crack = lp(noise(0.25), 3500) * np.exp(-np.arange(int(0.25 * SR)) / SR / 0.04)
    out = body * level
    out[: len(crack)] += crack * 0.5
    return reverb(out, rt=2.2, mix=0.28, wet_lp=2500)[: n + int(0.5 * SR)]


def riser(d, f0=200, f1=6000, level=0.5):
    t = t_(d)
    n = noise(d)
    k = (f1 / f0) ** (1 / d)
    # filtro passa-banda varrido (aprox. por blocos)
    out = np.zeros(len(n))
    B = 1024
    for i in range(0, len(n), B):
        f = min(f0 * k ** (i / SR), 0.45 * SR)
        sos = signal.butter(2, [f * 0.7, min(f * 1.4, 0.49 * SR)], "bp", fs=SR, output="sos")
        out[i:i + B] = signal.sosfilt(sos, n[i:i + B]) if i == 0 else signal.sosfilt(sos, n[max(0, i - 256):i + B])[-len(out[i:i + B]):]
    out = out / (np.max(np.abs(out)) + 1e-9)
    return out * (t / d) ** 2.2 * level


def whoosh(d=0.6, level=0.6, up=True):
    t = t_(d)
    n = noise(d)
    out = np.zeros(len(n))
    B = 512
    for i in range(0, len(n), B):
        x = i / len(n)
        f = 250 * (14 ** (x if up else 1 - x))
        sos = signal.butter(2, [f * 0.6, min(f * 1.6, 0.49 * SR)], "bp", fs=SR, output="sos")
        out[i:i + B] = signal.sosfilt(sos, n[i:i + B])
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return out / (np.max(np.abs(out)) + 1e-9) * e * level


def glitch(d=0.3, level=0.5, seed=0):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    out = np.zeros(n)
    i = 0
    while i < n:
        seg = int(r.uniform(0.008, 0.045) * SR)
        kind = r.integers(0, 3)
        tt = np.arange(seg) / SR
        if kind == 0:
            s = np.sign(np.sin(2 * np.pi * r.uniform(200, 2400) * tt))
        elif kind == 1:
            s = r.standard_normal(seg)
        else:
            s = np.sin(2 * np.pi * r.uniform(800, 5000) * tt) * np.sign(r.standard_normal())
        out[i:i + seg] = s[: n - i] * r.uniform(0.3, 1) if r.random() > 0.2 else 0
        i += seg
    out = bitcrush(out, 4, 3)
    return hp(out, 300) * level


def blip(f, d=0.07, level=0.4):
    t = t_(d)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
    return s * np.exp(-t / (d * 0.35)) * level


def buzz(d=0.38, level=0.8):
    """vibração de celular sobre mesa: motor ~170 Hz + ruído de contato da mesa."""
    t = t_(d)
    motor = np.sign(np.sin(2 * np.pi * 168 * t)) * 0.4 + np.sin(2 * np.pi * 168 * t) * 0.6
    motor = lp(motor, 900)
    am = 0.65 + 0.35 * np.sin(2 * np.pi * 26 * t)
    rattle = bp(noise(d), 1500, 5200) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 52 * t))) * 0.25
    e = np.minimum(t / 0.01, 1) * np.minimum((d - t) / 0.03, 1)
    return (motor * am + rattle) * e * level


def ring_tone(d=0.8, level=0.25):
    t = t_(d)
    s = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 20 * t)))
    return lp(s, 3000) * np.minimum(t / 0.01, 1) * np.minimum((d - t) / 0.02, 1) * level


def heartbeat(level=0.9):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    lub = np.sin(2 * np.pi * 52 * t) * np.exp(-t / 0.07)
    dub = np.sin(2 * np.pi * 44 * (t - 0.17)) * np.exp(-np.clip(t - 0.17, 0, None) / 0.06) * (t > 0.17) * 0.75
    return (lub + dub) * level


# ---------------------------------------------------------------- vozes
def load_voice(name, t0):
    x, sr = sf.read(f"{ROOT}/audio_src/{name}.wav")
    x = signal.resample_poly(x, SR, sr)
    return x


def narrator_fx(x):
    x = hp(x, 70)
    # realce de graves (corpo) e presença
    low = lp(x, 180) * 0.3
    pres = bp(x, 2200, 4500) * 0.35
    y = x + low + pres
    # compressão simples
    e = np.maximum(smooth_env(y, 0.02), 1e-4)
    g = np.where(e > 0.12, (0.12 / e) ** 0.55, 1.0)
    g = lp(g, 40, 1)
    y = y * g
    y = reverb(y, rt=0.9, mix=0.07, wet_lp=4500, seed=11)
    return y / (np.max(np.abs(y)) + 1e-9) * 0.9


def phone_fx(x):
    # voz saindo de uma ligação: banda 300–3400 Hz + leve distorção + ruído de linha
    y = bp(x, 300, 3400, 3)
    y = np.tanh(y * 3.2) * 0.7
    y += bp(noise(len(y) / SR), 2000, 6000) * 0.012
    y = reverb(y, rt=0.7, mix=0.22, wet_lp=3000, seed=21)
    return y / (np.max(np.abs(y)) + 1e-9) * 0.85


# ---------------------------------------------------------------- construção
def build_voices():
    narr = np.zeros(N)
    call = np.zeros(N)
    spans = {}
    for name, t0 in SYNC["voices"].items():
        raw = load_voice(name, t0)
        fx = phone_fx(raw) if name == "call" else narrator_fx(raw)
        dur = len(raw) / SR
        spans[name] = (t0, t0 + dur)
        place(call if name == "call" else narr, fx, t0, 1.0)
    # narração dobrada de leve (voz mais "cinematográfica"): cópia 12ms depois, pitch -> sub-oitava suave
    sub = lp(narr, 220) * 0.0
    return narr, call, spans


def build_sfx(spans, call_dry):
    sfx = np.zeros((N, 2))
    L = lambda m, t0, g=1.0, w=0.0: place_st(sfx, m, t0, g, w)

    # --- Cena 1: vibração, toque e impacto
    for tv in EV["vibrate"]:
        L(buzz(0.40, 0.9), tv, 1.0, 0.3)
    L(ring_tone(0.9, 0.18), 0.35, 1, 0.5)
    L(ring_tone(0.9, 0.18), 1.55, 1, 0.5)
    L(riser(0.62, 300, 5000, 0.45), EV["impact1"] - 0.62)
    L(boom(2.0, 120, 34, 1.0), EV["impact1"], 1.0)
    L(glitch(0.18, 0.5, 1), EV["impact1"] + 0.02, 0.8)

    # --- Transição 1→2
    L(whoosh(0.5, 0.7, True), EV["glitch12"] - 0.25, 1.0, 0.8)
    L(glitch(0.28, 0.6, 2), EV["glitch12"] - 0.04, 1.0)

    # --- Cena 2: fragmentos viajando até o núcleo (blips pentatônicos) + zumbido de processamento
    scale = [440, 523.25, 587.33, 659.25, 783.99, 880, 1046.5]
    for i in range(EV["fragmentCount"]):
        tt = EV["fragmentStart"] + i * EV["fragmentStep"]
        f = scale[(i * 3 + i // 4) % len(scale)]
        L(blip(f * (1.5 if i % 3 == 0 else 1), 0.09, 0.22), tt, 1.0, 0.6)
        L(blip(f / 2, 0.14, 0.12), tt + 0.02, 1.0, 0.2)
    hum = bp(noise(3.8), 100, 400) * np.linspace(0.0, 0.18, int(3.8 * SR))
    L(hum, 3.2, 1.0, 0.7)
    L(whoosh(0.9, 0.35, True), 5.6, 1.0, 1.0)

    # --- Cena 3: scanner, textos, subida de tensão
    for i, tt in enumerate([7.3, 8.5, 9.7]):
        L(sweep(300, 2400, 1.0) * np.sin(np.linspace(0, np.pi, int(1.0 * SR))) ** 2 * 0.13, tt, 1.0, 0.8)
    L(boom(1.2, 90, 36, 0.55), 7.3, 1.0)
    L(boom(1.0, 90, 36, 0.45), 9.1, 1.0)
    L(riser(1.0, 400, 7000, 0.4), 10.0)
    L(whoosh(0.4, 0.6, True), 10.7, 1.0, 1.0)
    L(glitch(0.1, 0.5, 4), 10.95)

    # --- Cena 4: toque, conexão e batimentos crescentes
    L(ring_tone(0.8, 0.22), EV["ringIn"], 1.0, 0.4)
    L(buzz(0.4, 0.5), EV["ringIn"] + 0.02, 1.0, 0.2)
    L(blip(1200, 0.03, 0.25), EV["callConnect"])
    L(blip(1800, 0.03, 0.2), EV["callConnect"] + 0.06)
    t = EV["heartStart"]
    bpm = 62.0
    while t < EV["cut"]:
        k = (t - EV["heartStart"]) / (EV["cut"] - EV["heartStart"])
        L(heartbeat(0.55 + 0.45 * k), t, 1.0)
        t += 60.0 / (bpm + 60 * k ** 1.2)
    # sombra tensa: tom agudo sutil + riser
    L(riser(3.9, 500, 9000, 0.55), 12.0)
    # corte seco antes da revelação
    # --- Cena 5: revelação com glitch brutal
    L(glitch(0.45, 0.8, 5), EV["reveal"] - 0.05)
    L(boom(2.4, 140, 30, 1.25), EV["reveal"], 1.0)
    L(whoosh(0.5, 0.8, False), EV["reveal"], 1.0, 1.0)
    # a voz da ligação "desfeita" pelo glitch: repetições granulares + pitch para baixo/cima
    g = call_dry[int(11.9 * SR): int(12.6 * SR)]
    for i, (off, st, ln) in enumerate([(0.10, 0.0, 0.07), (0.20, 0.02, 0.07), (0.28, 0.1, 0.05), (0.50, 0.3, 0.12), (0.68, 0.3, 0.04), (0.74, 0.3, 0.04), (0.84, 0.55, 0.15)]):
        seg = g[int(st * SR): int((st + ln) * SR)]
        if len(seg) == 0:
            continue
        seg = signal.resample_poly(seg, 3, 4) if i % 2 else seg
        L(bitcrush(fade(seg, 0.003, 0.01), 6, 2) * 0.9, EV["reveal"] + off, 1.0, 0.4)
    L(glitch(0.15, 0.5, 6), EV["textArtificial"] - 0.02)
    L(boom(1.8, 100, 34, 0.9), EV["textArtificial"], 1.0)
    for i, tt in enumerate(np.arange(16.5, 17.0, 0.07)):
        L(blip(900 + 220 * (i % 5), 0.04, 0.12), tt, 1.0, 0.8)

    # --- Cena 6: onda vermelha e pergunta final
    L(whoosh(1.4, 0.6, True), 19.95, 1.0, 1.0)
    L(boom(1.5, 60, 33, 0.6), 20.0, 1.0)
    L(riser(2.6, 300, 4000, 0.3), 22.0)
    # impacto final (mais grave) + glitch curto
    L(boom(1.3, 150, 28, 1.35), EV["finalHit"], 1.0)
    L(glitch(0.2, 0.7, 9), EV["finalHit"] + 0.03)
    return sfx


def place_st(buf, mono, t0, g=1.0, width=0.0):
    st = stereo(mono, width) if width > 0 else np.stack([mono, mono], 1)
    i = int(t0 * SR)
    n = min(len(st), len(buf) - i)
    if n > 0 and i >= 0:
        buf[i:i + n] += st[:n] * g


def build_music():
    """Trilha: drone sombrio em Lá menor + pulsos eletrônicos que crescem até a revelação (16s),
    queda total em 18,95–20 s e retorno sombrio até o golpe final."""
    mus = np.zeros(N)
    t = np.arange(N) / SR

    # intensidade global 0..1 (cresce até 16s; vale na revelação; retorna)
    inten = np.interp(t, [0, 3, 7, 11, 15.9, 16.0, 18.9, 20.0, 22, 24.7, 25], [0.25, 0.35, 0.5, 0.7, 1.0, 0.55, 0.0, 0.35, 0.55, 1.0, 0.0])

    # Drone: A1 + E2 serrilhadas desafinadas, com filtro que abre com a intensidade
    drone = np.zeros(N)
    for f, g in [(55.0, 1.0), (55.3, 0.8), (54.7, 0.8), (82.4, 0.5), (110.0, 0.35), (164.8, 0.2)]:
        drone += saw(f, DUR) * g
    out = np.zeros(N)
    B = 2048
    for i in range(0, N, B):
        fc = 140 + 1500 * inten[min(i, N - 1)] ** 1.6
        sos = signal.butter(2, fc, "lp", fs=SR, output="sos")
        if i == 0:
            zi = signal.sosfilt_zi(sos) * 0
        out[i:i + B], zi = signal.sosfilt(sos, drone[i:i + B], zi=zi)
    out *= 0.16 * (0.35 + 0.65 * inten)
    # lento tremolo para sensação de respiração
    out *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t)
    mus += out

    # sub-grave contínuo
    mus += np.sin(2 * np.pi * 36.7 * t) * 0.16 * inten

    # Pulsos eletrônicos (colcheias 118 bpm) - baixo pulsante A, A, C, A / E
    bpm = 118.0
    step = 60.0 / bpm / 2
    seq = [55.0, 55.0, 65.4, 55.0, 55.0, 82.4, 55.0, 49.0]
    k = 0
    tt = 1.0
    while tt < 24.7:
        i_ = inten[int(tt * SR)]
        in_silence = 16.0 <= tt < 20.0 and not (16.0 <= tt < 16.5)
        if i_ > 0.28 and not (18.9 <= tt < 20.0):
            f = seq[k % len(seq)]
            d = step * 0.9
            n = int(d * SR)
            tn = np.arange(n) / SR
            s = (np.sign(np.sin(2 * np.pi * f * tn)) * 0.5 + saw(f, d) * 0.5)
            s = lp(s, 250 + 1400 * i_ ** 2) * np.exp(-tn / (d * 0.55))
            gain = 0.20 * i_ ** 1.2
            if 16.5 <= tt < 18.9:
                gain *= 0.35
            place(mus, s, tt, gain)
        tt += step
        k += 1

    # Arpejo agudo (pluck) cresce na cena 2-4
    arp_notes = [220.0, 261.63, 329.63, 392.0, 329.63, 261.63, 440.0, 329.63]
    tt = 3.0
    k = 0
    st2 = step / 2
    while tt < 15.9:
        i_ = inten[int(tt * SR)]
        if tt > 3.2 and i_ > 0.4:
            f = arp_notes[k % len(arp_notes)] * (2 if k % 5 == 0 and tt > 8 else 1)
            d = 0.22
            n = int(d * SR)
            tn = np.arange(n) / SR
            s = (saw(f, d) * 0.6 + np.sin(2 * np.pi * f * tn) * 0.4) * np.exp(-tn / 0.06)
            s = lp(s, 2800)
            place(mus, reverb(s, 0.8, 0.35, 3500, seed=5), tt, 0.055 * i_)
        tt += st2
        k += 1

    # Pad sombrio no retorno (20–24.7)
    pad = np.zeros(N)
    for f in [110.0, 130.8, 164.8]:
        s = saw(f, 5.0) + saw(f * 1.004, 5.0)
        s = lp(s, 700)
        place(pad, s * np.linspace(0.0, 1, len(s)) ** 1.5, 20.0, 1.0)
    mus += pad * 0.045

    # Tick de hi-hat sutil de 11 a 16
    tt = 11.0
    while tt < 15.9:
        h = hp(noise(0.04), 7000) * np.exp(-np.arange(int(0.04 * SR)) / SR / 0.012)
        place(mus, h, tt, 0.05 * inten[int(tt * SR)])
        tt += step
    mus = reverb(mus, rt=2.0, mix=0.18, wet_lp=3500, seed=8, tail=False)

    # silêncio total (breve) após a revelação
    sil = np.interp(t, [0, 18.9, 19.0, 19.85, 20.0, 25], [1, 1, 0.0, 0.0, 1, 1])
    sil = np.where((t > 18.9) & (t < 20.0), np.where(t < 19.0, np.interp(t, [18.9, 19.0], [1, 0]), np.where(t > 19.85, np.interp(t, [19.85, 20.0], [0, 1]), 0)), 1)
    mus *= sil
    # corte seco 15.88–16.0 (sensação de "vácuo" antes do impacto)
    cut = np.where((t > EV["cut"]) & (t < EV["reveal"]), 0.0, 1.0)
    mus *= lp(cut, 200, 1)
    # fim: fade rápido após golpe final
    mus *= np.where(t > 24.9, np.interp(t, [24.9, 25.0], [1, 0]), 1)
    return stereo(mus, 1.0)


# ---------------------------------------------------------------- mix & export
def main():
    os.makedirs(f"{ROOT}/public/audio", exist_ok=True)
    os.makedirs(f"{ROOT}/src/generated", exist_ok=True)
    narr, call, spans = build_voices()
    # ducking da música/efeitos pela voz
    e = smooth_env(narr + call, 0.06)
    e = np.clip(e / (np.max(e) * 0.5), 0, 1)
    duck = lp(1 - 0.55 * e, 8, 1)

    sfx = build_sfx(spans, call)
    music = build_music()

    v = stereo(narr, 0.0) * 1.0
    c = stereo(call, 0.35) * 0.95
    mix = music * duck[:, None] * 0.95 + sfx * (0.8 + 0.2 * duck[:, None]) * 0.7 + v + c
    # remove DC, limitador suave
    mix = hp(mix.T, 25).T
    mix = np.tanh(mix * 0.9) / np.tanh(0.9)

    # fade de entrada para evitar clique
    mix[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))[:, None]
    mix[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))[:, None]

    stems = {"music": music * duck[:, None], "sfx": sfx, "narration": stereo(narr), "call": stereo(call, 0.35)}
    for k_, v_ in stems.items():
        sf.write(f"{ROOT}/public/audio/{k_}.wav", np.clip(v_, -1, 1), SR, subtype="PCM_16")
    sf.write(f"{ROOT}/public/audio/master_raw.wav", np.clip(mix, -1, 1), SR, subtype="PCM_16")

    # envelope por frame (voz + graves da trilha) para visuais reativos
    def frame_env(x, win=1 / FPS):
        n = int(DUR * FPS)
        out = np.zeros(n)
        w = int(win * SR)
        for i in range(n):
            seg = x[i * w * 1: i * w + w] if False else x[int(i * SR / FPS): int((i + 1) * SR / FPS)]
            out[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
        return out

    mono = lambda s: s.mean(1) if s.ndim > 1 else s
    env = {
        "voice": frame_env(narr),
        "call": frame_env(call),
        "music": frame_env(mono(music * duck[:, None])),
        "sfx": frame_env(mono(sfx)),
    }
    for k_ in env:
        env[k_] = env[k_] / (np.percentile(env[k_], 99.5) + 1e-9)
        env[k_] = np.clip(env[k_], 0, 1)
    # amplitude de mais alta resolução (4 sub-frames por frame) p/ ondas bem fluidas
    def hi(x, sub=4):
        n = int(DUR * FPS) * sub
        o = np.zeros(n)
        for i in range(n):
            seg = x[int(i * SR / FPS / sub): int((i + 1) * SR / FPS / sub)]
            o[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
        return o / (np.percentile(o, 99.5) + 1e-9)
    hv = np.clip(hi(narr + call), 0, 1)
    json.dump({"fps": FPS, **{k_: [round(float(a), 3) for a in v_] for k_, v_ in env.items()},
               "hires": [round(float(a), 3) for a in hv], "sub": 4},
              open(f"{ROOT}/src/generated/envelope.json", "w"))

    # legendas (tempo das palavras ponderado por sílabas)
    TEXT = {
        "n1a": "E se sua mãe te ligasse pedindo socorro?",
        "n1b": "Mas não fosse ela.",
        "n2": "A inteligência artificial captura sua voz, e a reconstrói.",
        "n3": "Apenas alguns segundos de áudio podem ser suficientes para um golpe.",
        "call": "Filho... preciso da sua ajuda...",
        "n5": "A voz era artificial.",
        "n6a": "Sua voz pode ser clonada.",
        "n6b": "Você saberia identificar uma ligação falsa?",
    }
    def syl(w):
        w2 = re.sub(r"[^a-záàâãéêíóôõúüç]", "", w.lower())
        return max(1, len(re.findall(r"[aeiouáàâãéêíóôõúü]+", w2)))
    caps = []
    for name, (a, b) in spans.items():
        words = TEXT[name].split()
        wts = [syl(w) + (0.6 if re.search(r"[.,?!…]$", w) else 0) + 0.25 for w in words]
        tot = sum(wts)
        c = a
        ws = []
        for w, wt in zip(words, wts):
            d = (b - a) * wt / tot
            ws.append({"w": w, "s": round(c, 3), "e": round(c + d, 3)})
            c += d
        caps.append({"id": name, "start": round(a, 3), "end": round(b, 3), "words": ws, "kind": "call" if name == "call" else "narr"})
    json.dump(caps, open(f"{ROOT}/src/generated/captions.json", "w"), ensure_ascii=False, indent=1)
    print("vozes:", {k_: (round(a, 2), round(b, 2)) for k_, (a, b) in spans.items()})
    print("pico mix:", float(np.max(np.abs(mix))))


if __name__ == "__main__":
    main()

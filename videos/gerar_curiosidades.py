#!/usr/bin/env python3
"""Short 9:16 de 25 s: 3 curiosidades do Minecraft com sprites animados (fundo transparente).

Sprites pixel-art desenhados por código, efeitos (pop, brilho, glitch, partículas),
voz espeak-ng offline, legendas palavra a palavra, música e SFX sintetizados.
Uso: python3 gerar_curiosidades.py [saida.mp4]
"""
import ctypes, math, random, subprocess, sys, wave, os
import numpy as np
import espeakng_loader
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "curiosidades_minecraft.mp4"
FPS, W, H, S = 30, 270, 480, 4
FW, FH = W * S, H * S
SR = 44100
DURATION = 25.0
NF = int(DURATION * FPS)

SCRIPT = [
    ("Três curiosidades do Minecraft que você não sabia!",
     "3 CURIOSIDADES DO MINECRAFT QUE VOCÊ NÃO SABIA!"),
    ("Número um: o Creeper nasceu de um erro! Era pra ser um porco.",
     "Nº 1: O CREEPER NASCEU DE UM ERRO! ERA PRA SER UM PORCO."),
    ("Número dois: o Enderman fica furioso se você olhar nos olhos dele!",
     "Nº 2: O ENDERMAN FICA FURIOSO SE VOCÊ OLHAR NOS OLHOS DELE!"),
    ("Número três: em dois mil e catorze, a Microsoft comprou o jogo por dois bilhões e meio de dólares!",
     "Nº 3: EM 2014, A MICROSOFT COMPROU O JOGO POR US$ 2,5 BILHÕES!"),
    ("Segue pra mais curiosidades!", "SEGUE PRA MAIS CURIOSIDADES!"),
]

# ---------------------------------------------------------------- voz (espeak)
_lib = ctypes.CDLL(espeakng_loader.get_library_path())
_lib.espeak_Initialize.restype = ctypes.c_int
_RATE = _lib.espeak_Initialize(1, 0, espeakng_loader.get_data_path().encode(), 0)
_buf = []
_CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
def _cb(wav, n, ev):
    if wav and n > 0: _buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
    return 0
_cbf = _CB(_cb)
_lib.espeak_SetSynthCallback(_cbf)
_lib.espeak_SetVoiceByName(b"pt-br")
_lib.espeak_SetParameter(3, 38, 0)

def synth_all(wpm):
    _lib.espeak_SetParameter(1, int(wpm), 0)
    out = []
    for fala, _ in SCRIPT:
        _buf.clear(); b = fala.encode()
        _lib.espeak_Synth(b, len(b) + 1, 0, 1, 0, 1, None, None); _lib.espeak_Synchronize()
        a = np.concatenate(_buf).astype(np.float32) / 32768.0
        idx = np.where(np.abs(a) > 0.01)[0]; a = a[idx[0]:idx[-1] + 1]
        out.append(np.interp(np.arange(0, len(a), _RATE / SR), np.arange(len(a)), a).astype(np.float32))
    return out

GAP, T0, VOICE_END = 0.32, 0.3, 23.6
wpm = 190.0
for _ in range(3):                      # ajusta a velocidade para caber nos 25 s
    clips = synth_all(wpm)
    speech = sum(len(c) for c in clips) / SR
    target = VOICE_END - T0 - GAP * (len(clips) - 1)
    wpm = min(300, max(130, wpm * speech / target))
    if abs(speech - target) < 0.15: break
clips = synth_all(wpm)
phr, t = [], T0
for c in clips:
    d = len(c) / SR; phr.append((t, t + d)); t += d + GAP
assert phr[-1][1] < DURATION - 0.4, "fala não coube em 25 s"
TOTAL = DURATION
starts = [p[0] for p in phr]
ends = [phr[i + 1][0] if i + 1 < len(phr) else DURATION for i in range(len(phr))]

words = []
for (_, cap), (a, b) in zip(SCRIPT, phr):
    ws = cap.split(); wl = np.array([len(w) + 2 for w in ws], float)
    e = a + (b - a) * np.concatenate([[0], np.cumsum(wl)]) / wl.sum()
    words += [(w, e[i], e[i + 1]) for i, w in enumerate(ws)]
groups, i = [], 0
while i < len(words):
    n = 1
    while i + n < len(words) and n < 3 and sum(len(x[0]) for x in words[i:i + n + 1]) + n <= 17 \
            and words[i + n - 1][0][-1] not in "?!.,:":
        n += 1
    groups.append(words[i:i + n]); i += n

# eventos
T_MORPH = starts[1] + 1.9          # porco -> creeper
T_BLINK = [starts[2] + 1.6, starts[2] + 3.0]   # enderman teleporta
T_COINS = starts[3] + 1.3

# ---------------------------------------------------------------------- áudio
def mix_audio(path):
    n = int(TOTAL * SR); rng = np.random.default_rng(2)
    voice = np.zeros(n, np.float32)
    for c, (a, _) in zip(clips, phr):
        s = int(a * SR); voice[s:s + len(c)] += c
    voice /= max(0.01, np.abs(voice).max()) / 0.95
    tt = np.arange(n) / SR; beat = 60 / 150; step = beat / 2
    prog = [57, 53, 48, 55]; music = np.zeros(n, np.float32)
    sq = lambda f, ph: np.sign(np.sin(2 * np.pi * f * ph))
    for k in range(int(TOTAL / step) + 1):
        ch = prog[(k // 8) % 4]; s0, s1 = int(k * step * SR), min(n, int((k + 1) * step * SR))
        if s0 >= n: break
        ph = tt[s0:s1] - k * step
        bass = sq(440 * 2 ** ((ch - 12 - 69) / 12), tt[s0:s1]) * np.exp(-ph * 9) * 0.5
        arp = [0, 4 if ch != 57 else 3, 7, 12][k % 4]
        lead = sq(440 * 2 ** ((ch + 12 + arp - 69) / 12), tt[s0:s1]) * np.exp(-ph * 14) * 0.35
        music[s0:s1] += (bass + lead).astype(np.float32)
    music *= 0.10
    env = np.convolve(np.abs(voice), np.ones(2205) / 2205, "same")
    music *= (1 - 0.55 * np.clip(env * 6, 0, 1)).astype(np.float32)
    sfx = np.zeros(n, np.float32)
    def put(t0, x):
        s = int(t0 * SR); x = x[:max(0, n - s)]
        if s >= 0: sfx[s:s + len(x)] += x
    def sweep(f0, f1, dur, vol, decay=10):
        d = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * (f0 + (f1 - f0) * d / dur) * d) * np.exp(-d * decay) * vol).astype(np.float32)
    for s0 in starts: put(s0, sweep(250, 1200, 0.22, 0.5, 14))          # pop de cada cena
    # glitch (estática crepitante) antes do morph
    d = np.arange(int(0.7 * SR)) / SR
    nz = rng.standard_normal(len(d)).astype(np.float32)
    gate = (np.sin(2 * np.pi * 23 * d) > 0.2).astype(np.float32)
    put(T_MORPH - 0.55, nz * gate * np.linspace(0.05, 0.4, len(d)).astype(np.float32))
    put(T_MORPH, sweep(900, 120, 0.4, 0.6, 7))
    for tb in T_BLINK: put(tb, sweep(1800, 200, 0.35, 0.5, 8)); put(tb + 0.35, sweep(200, 1800, 0.25, 0.4, 10))
    for k in range(14):                                                  # moedas
        put(T_COINS + 0.12 * k + rng.uniform(0, 0.05), sweep(1900, 2300, 0.12, 0.25, 22))
    for g in groups: put(g[0][1], sweep(1500, 1500, 0.05, 0.12, 60))
    for k, f in enumerate((523, 659, 784, 1047)): put(starts[4] + 0.1 * k, sweep(f, f, 0.2, 0.25, 9))
    out = np.tanh((voice + music + sfx) * 1.1)
    out = (out / max(1e-6, np.abs(out).max()) * 0.92 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())

# ------------------------------------------------------------------- utilidades
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x):                                   # pop com overshoot
    x = min(1, max(0, x)); c1 = 2.2; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def R(d, x, y, w, h, c): d.rectangle([x, y, x + w - 1, y + h - 1], fill=c)

# ----------------------------------------------------------------------- sprites
def spr_grass():
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im); g = random.Random(5)
    R(d, 0, 0, 16, 16, (121, 85, 58))
    for _ in range(30): R(d, g.randrange(16), g.randrange(4, 16), 1, 1, g.choice(((97, 66, 44), (140, 100, 70))))
    R(d, 0, 0, 16, 5, (98, 174, 62))
    for x in range(16):
        if g.random() < .5: R(d, x, 5, 1, g.randrange(1, 3), (98, 174, 62))
    for _ in range(14): R(d, g.randrange(16), g.randrange(0, 5), 1, 1, g.choice(((76, 150, 48), (130, 205, 80))))
    d.rectangle([0, 0, 15, 15], outline=(0, 0, 0, 90))
    return im

def spr_pig():
    im = Image.new("RGBA", (28, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in (2, 8, 16, 21): R(d, x, 13, 3, 5, (232, 130, 142))
    R(d, 3, 4, 20, 10, (245, 160, 170)); R(d, 20, 3, 8, 9, (245, 160, 170)); R(d, 25, 7, 3, 4, (232, 126, 140))
    R(d, 22, 5, 2, 2, (30, 30, 30)); R(d, 26, 8, 1, 1, (140, 60, 70))
    return im

def spr_creeper():
    im = Image.new("RGBA", (16, 28), (0, 0, 0, 0)); d = ImageDraw.Draw(im); g = random.Random(3)
    R(d, 2, 21, 5, 7, (60, 150, 52)); R(d, 9, 21, 5, 7, (60, 150, 52))
    R(d, 4, 10, 8, 13, (72, 165, 60)); R(d, 1, 21, 4, 7, (66, 158, 56)); R(d, 11, 21, 4, 7, (66, 158, 56))
    R(d, 3, 0, 10, 10, (84, 190, 70))
    for _ in range(26): R(d, 3 + g.randrange(10), g.randrange(10), 2, 2, g.choice(((58, 140, 50), (110, 215, 90))))
    R(d, 4, 2, 3, 3, (15, 30, 15)); R(d, 9, 2, 3, 3, (15, 30, 15))
    R(d, 7, 5, 2, 5, (15, 30, 15)); R(d, 6, 7, 4, 3, (15, 30, 15))
    return im

def spr_enderman():
    im = Image.new("RGBA", (16, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(im); k = (22, 22, 26)
    R(d, 4, 24, 3, 20, k); R(d, 9, 24, 3, 20, k)                # pernas finas
    R(d, 4, 10, 8, 14, (14, 14, 18))                            # torso
    R(d, 1, 10, 2, 22, k); R(d, 13, 10, 2, 22, k)               # braços longos
    R(d, 3, 0, 10, 10, k)                                       # cabeça
    R(d, 3, 5, 10, 1, (8, 8, 10))
    R(d, 4, 3, 3, 2, (255, 120, 255)); R(d, 9, 3, 3, 2, (255, 120, 255))   # olhos
    R(d, 4, 3, 1, 2, (255, 255, 255)); R(d, 9, 3, 1, 2, (255, 255, 255))
    return im

def spr_diamond():
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(8, 1), (14, 6), (8, 15), (2, 6)], fill=(60, 220, 215))
    d.polygon([(8, 1), (14, 6), (8, 7)], fill=(150, 250, 245)); d.polygon([(8, 1), (2, 6), (8, 7)], fill=(110, 240, 235))
    d.polygon([(8, 7), (14, 6), (8, 15)], fill=(30, 170, 175)); d.polygon([(2, 6), (8, 7), (8, 15)], fill=(45, 195, 195))
    d.line([(8, 1), (14, 6), (8, 15), (2, 6), (8, 1)], fill=(15, 90, 100))
    R(d, 5, 4, 2, 1, (255, 255, 255))
    return im

def spr_coin():
    im = Image.new("RGBA", (8, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    R(d, 1, 0, 6, 8, (255, 200, 40)); R(d, 0, 1, 8, 6, (255, 200, 40)); R(d, 2, 1, 4, 6, (255, 230, 100))
    R(d, 3, 2, 2, 4, (230, 160, 20))
    return im

def spr_pill(sz=(40, 14), c=(210, 40, 40)):
    return None

SP = dict(grass=spr_grass(), pig=spr_pig(), creeper=spr_creeper(), ender=spr_enderman(),
          diamond=spr_diamond(), coin=spr_coin())

# ------------------------------------------------------------------ composição
def place(big, spr, cx, cy, h, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, glow=None, gi=0.9, tint=None):
    w = max(2, int(spr.width / spr.height * h * sx)); hh = max(2, int(h * sy))
    s = spr.resize((w, hh), Image.NEAREST)
    if tint is not None:
        a = s.getchannel("A"); s = Image.composite(Image.new("RGBA", s.size, tint + (255,)), s, a.point(lambda v: 255 if v else 0))
        s.putalpha(a)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1: s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    if glow:
        pad = 70; lay = Image.new("RGBA", (s.width + 2 * pad, s.height + 2 * pad), (0, 0, 0, 0))
        m = Image.new("L", lay.size, 0); m.paste(s.getchannel("A"), (pad, pad))
        m = m.filter(ImageFilter.GaussianBlur(28)).point(lambda v: min(255, int(v * 2.2 * gi * alpha)))
        lay.paste(Image.new("RGBA", lay.size, glow + (255,)), (0, 0), m)
        big.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)
    big.paste(s, (int(cx - s.width / 2), int(cy - s.height / 2)), s)

def glitch(spr_img, amt, rng):
    """desloca fatias horizontais + fantasma colorido; retorna novo sprite maior."""
    w, h = spr_img.size; out = Image.new("RGBA", (w + 8, h), (0, 0, 0, 0))
    for (col, off) in (((255, 0, 80), -2), ((0, 220, 255), 2)):
        a = spr_img.getchannel("A"); g = Image.new("RGBA", spr_img.size, col + (150,)); g.putalpha(a.point(lambda v: v // 2))
        out.alpha_composite(g, (4 + int(off * amt * 2), 0))
    y = 0
    while y < h:
        sh = rng.randint(1, max(1, h // 6)); sl = spr_img.crop((0, y, w, min(h, y + sh)))
        dx = int(rng.uniform(-1, 1) * amt * 4) if rng.random() < min(1, amt) else 0
        out.alpha_composite(sl, (4 + dx, y)); y += sh
    return out

def sparkles(d, t, cx, cy, rad, n, seed, cols=((255, 255, 255), (255, 226, 40), (120, 255, 200))):
    r = random.Random(seed)
    for i in range(n):
        ang, rr, ph, sp = r.uniform(0, 6.28), r.uniform(.5, 1) * rad, r.uniform(0, 6.28), r.uniform(2, 5)
        k = (math.sin(t * sp + ph) + 1) / 2
        if k < 0.35: continue
        x = cx + math.cos(ang + t * 0.4) * rr; y = cy + math.sin(ang + t * 0.4) * rr * 0.8
        z = int(10 + 22 * k); c = cols[i % len(cols)]
        d.rectangle([x - z, y - 4, x + z, y + 4], fill=c); d.rectangle([x - 4, y - z, x + 4, y + z], fill=c)

def burst(d, t, t0, cx, cy, cols, n=48, life=0.9, spd=(300, 900), size=(12, 26), seed=1, grav=900):
    k = t - t0
    if k < 0 or k > life: return
    r = random.Random(seed)
    for _ in range(n):
        ang, v, sz = r.uniform(0, 6.28), r.uniform(*spd), r.randrange(*size); c = r.choice(cols)
        x = cx + math.cos(ang) * v * k; y = cy + math.sin(ang) * v * k + grav * k * k * 0.5
        a = 1 - k / life
        z = max(2, int(sz * a)); d.rectangle([x, y, x + z, y + z], fill=c)

# ------------------------------------------------------------------- texto
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fc = {}
def font(sz):
    sz = max(8, int(sz))
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FONT_B, sz)
    return _fc[sz]
def tstroke(d, xy, s, f, fill, stroke=9, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)

def draw_caption(d, t):
    g = next((g for g in groups if g[0][1] - 0.02 <= t < g[-1][2] + 0.10), None)
    if g is None: return
    size = 118
    while True:
        f = font(size); ws = [d.textlength(w[0], font=f) for w in g]; sp = d.textlength(" ", font=f) + max(8, size // 11) * 2
        tot = sum(ws) + sp * (len(g) - 1)
        if tot <= 960 or size < 50: break
        size -= 6
    x = FW / 2 - tot / 2; y = 1330
    for (w, a, b), wd in zip(g, ws):
        act = a <= t < b
        pop = 1 + 0.18 * math.sin(math.pi * (t - a) / 0.14) if act and t - a < 0.14 else 1.0
        tstroke(d, (x + wd / 2, y), w, font(size * pop), (255, 226, 40) if act else (255, 255, 255), stroke=max(8, size // 11))
        x += wd + sp

def sticker(big, text, cx, cy, rot, fill, size=64, scale=1.0, fg=(255, 255, 255)):
    f = font(size * scale); tmp = Image.new("RGBA", (900, 260), (0, 0, 0, 0)); dd = ImageDraw.Draw(tmp)
    tw = dd.textlength(text, font=f); bw, bh = tw + 80, size * scale + 60
    dd.rounded_rectangle([450 - bw / 2, 130 - bh / 2, 450 + bw / 2, 130 + bh / 2], radius=26, fill=fill, outline=(0, 0, 0), width=9)
    dd.text((450, 130), text, font=f, fill=fg, anchor="mm")
    tmp = tmp.rotate(rot, resample=Image.BICUBIC)
    big.paste(tmp, (int(cx - 450), int(cy - 130)), tmp)

# ------------------------------------------------------------------- fundo
rnd = random.Random(9)
stars = [(rnd.randrange(W), rnd.randrange(0, 380), rnd.random() * 6) for _ in range(60)]
clouds = [(rnd.randrange(0, 600), rnd.randrange(40, 330), rnd.randrange(30, 60)) for _ in range(6)]
SCENE_BG = [((40, 110, 200), (150, 215, 255)),      # dia
            ((50, 130, 60), (150, 230, 140)),      # creeper: verde
            ((95, 45, 150), (190, 110, 225)),        # enderman: roxo noturno
            ((15, 80, 110), (60, 200, 200)),       # diamante
            ((40, 110, 200), (150, 215, 255))]

def scene_idx(t):
    for i in range(len(starts) - 1, -1, -1):
        if t >= starts[i] - 0.0: return i
    return 0

def bg_color(t):
    i = scene_idx(t); k = ease((t - starts[i]) / 0.5) if i > 0 else 1
    a = SCENE_BG[max(0, i - 1)] if i > 0 else SCENE_BG[0]; b = SCENE_BG[i]
    top = tuple(a[0][j] + (b[0][j] - a[0][j]) * k for j in range(3))
    bot = tuple(a[1][j] + (b[1][j] - a[1][j]) * k for j in range(3))
    return top, bot

def draw_bg(d, t):
    top, bot = bg_color(t)
    for y in range(0, H, 4):
        k = y / H
        d.rectangle([0, y, W, y + 4], fill=tuple(int(top[j] + (bot[j] - top[j]) * k) for j in range(3)))
    i = scene_idx(t)
    if i == 2:
        for x, y, ph in stars:
            if math.sin(t * 3 + ph) > -0.3: d.rectangle([x, y, x + 1, y + 1], fill=(255, 255, 255))
    for cx, cy, cw in clouds:
        x = (cx - t * 8) % 700 - 100
        c = (255, 255, 255) if i != 2 else (110, 70, 150)
        d.rectangle([x, cy, x + cw, cy + 9], fill=c); d.rectangle([x + 8, cy - 7, x + cw - 10, cy], fill=c)
    # faixa de grama rolando
    cam = t * 60
    for ci in range(int(cam // 16) - 1, int(cam // 16) + 19):
        x = ci * 16 - cam
        d.rectangle([x, 440, x + 16, H], fill=(121, 85, 58)); d.rectangle([x, 440, x + 16, 445], fill=(98, 174, 62))
        d.rectangle([x, 440, x + 16, 441], fill=(130, 205, 80)); d.line([x, 440, x, H], fill=(70, 50, 35))

# ------------------------------------------------------------------- cenas
CX, CY = FW // 2, 800

def pill(big, i, t):
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([250, 150, FW - 250, 250], radius=24, fill=(20, 20, 24), outline=(255, 226, 40), width=8)
    label = ["MINECRAFT", "CURIOSIDADE 1 / 3", "CURIOSIDADE 2 / 3", "CURIOSIDADE 3 / 3", "MINECRAFT"][i]
    d.text((FW / 2, 200), label, font=font(48), fill=(255, 255, 255), anchor="mm")

def scene_effects(big, t, i):
    lt = t - starts[i]; d = ImageDraw.Draw(big)
    out = 1 - ease((t - (ends[i] - 0.22)) / 0.22) if i < len(starts) - 1 else 1.0   # sai antes da próxima cena
    appear = back(lt / 0.45) * out
    bob = math.sin(t * 3.2) * 18
    rng = random.Random(int(t * 30))
    if i in (0, 4):
        place(big, SP["grass"], CX, CY + bob, 520, sx=appear, sy=appear, rot=math.sin(t * 2.5) * 6,
              glow=(120, 255, 90), gi=0.8)
        sparkles(d, t, CX, CY, 420, 16, 4)
        if i == 0:
            k = back((lt - 0.15) / 0.4)
            tstroke(d, (CX, 410), "3 CURIOSIDADES", font(96 * k), (255, 226, 40), stroke=14)
            tstroke(d, (CX, 1160), "DO MINECRAFT", font(96 * k), (120, 255, 90), stroke=14)
        else:
            k = ease((lt - 0.2) / 0.3); sc = 1 + 0.05 * math.sin(t * 8)
            d.rounded_rectangle([CX - 400 * k, 1130 - 85 * k, CX + 400 * k, 1130 + 85 * k], radius=30, fill=(255, 40, 40),
                                outline=(0, 0, 0), width=10)
            if k > .8: d.text((CX, 1130), "SEGUIR  +  CURTIR", font=font(70 * sc), fill=(255, 255, 255), anchor="mm")
    elif i == 1:
        # porco -> glitch -> creeper
        pre = T_MORPH - 0.6
        if t < pre:
            place(big, SP["pig"], CX, CY + 60 + bob * .5, 360, sx=appear, sy=appear, glow=(255, 150, 190), gi=.7)
        elif t < T_MORPH + 0.5:
            k = ease((t - pre) / 0.6); amt = 1.5 if t < T_MORPH else 1.5 * (1 - (t - T_MORPH) / 0.5)
            src = SP["pig"] if t < T_MORPH else SP["creeper"]
            h = 360 if t < T_MORPH else 560
            g = glitch(src, amt, rng)
            # "alongando" altura/largura durante a transição
            sx_, sy_ = (1 - 0.35 * k, 1 + 0.5 * k) if t < T_MORPH else (1, 1)
            place(big, g, CX + rng.randint(-14, 14) * (amt > .3), CY + (60 if t < T_MORPH else 0), h, sx=sx_, sy=sy_,
                  glow=(120, 255, 100), gi=.9 * k)
        else:
            place(big, SP["creeper"], CX, CY + bob * .6, 560, sx=1 + .03 * math.sin(t * 6), sy=1,
                  glow=(120, 255, 100), gi=.9)
        burst(d, t, T_MORPH, CX, CY, [(120, 255, 100), (255, 255, 255), (40, 160, 50)], seed=3)
        if t > pre - 0.3 and out > 0:
            k = back((t - (pre - 0.3)) / 0.35)
            sticker(big, "BUG!", 800, 520, -12, (220, 30, 40), size=84, scale=k)
            if t > T_MORPH:
                k2 = back((t - T_MORPH - 0.1) / 0.35)
                sticker(big, "ALTURA ↔ LARGURA", 540, 1170, 3, (30, 30, 36), size=54, scale=k2, fg=(255, 226, 40))
    elif i == 2:
        # enderman teleporta; olhos brilham
        pos = CX
        if t >= T_BLINK[0] + 0.3: pos = CX + 230
        if t >= T_BLINK[1] + 0.3: pos = CX - 160
        vis = appear
        for tb in T_BLINK:
            if tb - 0.12 <= t < tb + 0.3:
                vis = 0 if rng.random() < 0.6 else 0.35
        place(big, SP["ender"], pos, CY + 30 + bob * .3, 740, sx=appear, sy=appear, alpha=vis, glow=(255, 150, 255),
              gi=1.1 + 0.5 * (math.sin(t * 9) > 0))
        for n, tb in enumerate(T_BLINK):
            src_x = CX if n == 0 else CX + 230
            dst_x = CX + 230 if n == 0 else CX - 160
            burst(d, t, tb, src_x, CY, [(220, 60, 255), (140, 20, 200), (255, 255, 255)], n=40, grav=-200, seed=5 + n)
            burst(d, t, tb + 0.25, dst_x, CY, [(220, 60, 255), (140, 20, 200), (255, 255, 255)], n=40, grav=-200, seed=8 + n)
        if lt > 0.8 and out > 0:
            k = back((lt - 0.8) / 0.35)
            sticker(big, "NÃO OLHE!", 800, 480, 10, (200, 30, 200), size=76, scale=k)
        # olhos observando: dois olhos grandes aparecem
        if lt > 1.0:
            kk = ease((lt - 1.0) / 0.3) * out
            for ex in (CX - 90, CX + 90):
                d.rectangle([ex - 55 * kk, 1160 - 18 * kk, ex + 55 * kk, 1160 + 18 * kk], fill=(255, 120, 255), outline=(0, 0, 0), width=6)
                d.rectangle([ex - 55 * kk, 1160 - 18 * kk, ex - 25 * kk, 1160 + 18 * kk], fill=(255, 255, 255))
    elif i == 3:
        place(big, SP["diamond"], CX, CY + bob, 520, sx=(appear * (1 + .08 * math.sin(t * 4))), sy=appear,
              rot=math.sin(t * 2.2) * 9, glow=(60, 240, 230), gi=1.0)
        sparkles(d, t, CX, CY, 400, 18, 12, ((255, 255, 255), (150, 250, 245), (255, 226, 40)))
        # chuva de moedas
        for n in range(22):
            r = random.Random(100 + n); t0 = T_COINS + r.uniform(0, 1.6); x = r.randrange(80, FW - 80)
            k = t - t0
            if 0 <= k < 2.2:
                y = -60 + k * 900 + 0
                wscale = abs(math.cos(k * 9 + n))
                place(big, SP["coin"], x, y, 90, sx=max(.15, wscale), glow=(255, 200, 40), gi=.4)
        if t > T_COINS - 0.3 and out > 0:
            k = back((t - (T_COINS - 0.3)) / 0.35)
            val = min(2.5, 2.5 * ease((t - T_COINS) / 1.6))
            sticker(big, f"US$ {val:.1f} BILHÕES".replace(".", ","), 540, 1130, -3, (20, 120, 60), size=66, scale=k)
            sticker(big, "2014", 820, 470, 9, (30, 30, 36), size=70, scale=k, fg=(255, 226, 40))

def render(fi):
    t = fi / FPS
    low = Image.new("RGB", (W, H)); draw_bg(ImageDraw.Draw(low), t)
    big = low.resize((FW, FH), Image.NEAREST).convert("RGBA")
    i = scene_idx(t)
    # cena anterior ainda saindo é tratada pelo "out"; desenha só a atual
    pill(big, i, t)
    scene_effects(big, t, i)
    d = ImageDraw.Draw(big)
    d.rectangle([0, FH - 26, FW, FH], fill=(0, 0, 0)); d.rectangle([0, FH - 26, int(FW * t / TOTAL), FH], fill=(120, 255, 90))
    draw_caption(d, t)
    return big.convert("RGB")

def main():
    wav = os.path.splitext(OUT)[0] + "_audio.wav"; mix_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FW}x{FH}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(DURATION), "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(NF): p.stdin.write(render(fi).tobytes())
    p.stdin.close(); p.wait(); os.remove(wav)
    print(f"ok: {OUT} ({DURATION}s, {NF} frames, voz {wpm:.0f} wpm, fala termina em {phr[-1][1]:.1f}s)")

if __name__ == "__main__":
    main()

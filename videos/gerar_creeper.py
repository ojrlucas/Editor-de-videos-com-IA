#!/usr/bin/env python3
"""Gera um short vertical (1080x1920) sobre a origem do Creeper, 100% por código.

Cenário: pixel-art estilo Minecraft desenhado com Pillow (não é gameplay real).
Voz: espeak-ng offline. Legendas palavra a palavra, música e SFX sintetizados.
Uso: python3 gerar_creeper.py [saida.mp4]
"""
import ctypes, math, random, subprocess, sys, wave, os
import numpy as np
import espeakng_loader
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "creeper.mp4"
FPS, W, H, S = 30, 270, 480, 4            # cena em baixa resolução, ampliada 4x
FW, FH = W * S, H * S
SR = 44100

# (fala para o TTS, texto exibido na legenda)
SCRIPT = [
    ("Você sabia que o Creeper do Minecraft nasceu de um erro?",
     "VOCÊ SABIA QUE O CREEPER NASCEU DE UM ERRO?"),
    ("Em dois mil e nove, o criador do jogo, Notch, tentava programar um porco.",
     "EM 2009, O CRIADOR TENTAVA PROGRAMAR UM PORCO"),
    ("Só que ele trocou a altura pela largura do modelo.",
     "SÓ QUE ELE TROCOU A ALTURA PELA LARGURA!"),
    ("E, em vez de um porquinho, saiu uma coisa alta, verde e esquisita.",
     "SAIU UMA COISA ALTA, VERDE E ESQUISITA"),
    ("Ele gostou tanto do bug, que deixou no jogo.",
     "ELE GOSTOU TANTO DO BUG QUE DEIXOU NO JOGO"),
    ("O monstro mais famoso do Minecraft é um porco que deu errado!",
     "O MONSTRO MAIS FAMOSO É UM PORCO QUE DEU ERRADO!"),
    ("Segue pra mais curiosidades!",
     "SEGUE PRA MAIS CURIOSIDADES!"),
]

# ---------------------------------------------------------------- voz (espeak)
def synth_all():
    lib = ctypes.CDLL(espeakng_loader.get_library_path())
    lib.espeak_Initialize.restype = ctypes.c_int
    rate = lib.espeak_Initialize(1, 0, espeakng_loader.get_data_path().encode(), 0)
    buf = []
    CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
    def cb(wav, n, ev):
        if wav and n > 0:
            buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
        return 0
    cbf = CB(cb)
    lib.espeak_SetSynthCallback(cbf)
    lib.espeak_SetVoiceByName(b"pt-br")
    lib.espeak_SetParameter(1, 200, 0)   # velocidade (wpm)
    lib.espeak_SetParameter(3, 38, 0)    # tom mais grave
    clips = []
    for fala, _ in SCRIPT:
        buf.clear()
        b = fala.encode("utf-8")
        lib.espeak_Synth(b, len(b) + 1, 0, 1, 0, 1, None, None)
        lib.espeak_Synchronize()
        a = np.concatenate(buf).astype(np.float32) / 32768.0
        # recorta silêncio das pontas
        idx = np.where(np.abs(a) > 0.01)[0]
        a = a[idx[0]:idx[-1] + 1]
        clips.append(np.interp(np.arange(0, len(a), rate / SR), np.arange(len(a)), a).astype(np.float32))
    return clips

clips = synth_all()
if os.environ.get("VOZ") == "xtts":                       # voz clonada (ver voz_xtts.py)
    import voz_xtts
    clips = [np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x).astype(np.float32)
             for x, sr in voz_xtts.sintetizar([f for f, _ in SCRIPT])]
    clips = [c[np.where(np.abs(c) > 0.01)[0][0]:np.where(np.abs(c) > 0.01)[0][-1] + 1] for c in clips]
GAP = 0.22
t = 0.35
phr = []                                   # (início, fim)
for c in clips:
    d = len(c) / SR
    phr.append((t, t + d))
    t += d + GAP
TOTAL = t + 0.9
NF = int(TOTAL * FPS)

# palavras da legenda com tempo proporcional ao tamanho
words = []                                  # (palavra, ini, fim, idx_frase)
for (_, cap), (a, b) in zip(SCRIPT, phr):
    ws = cap.split()
    wl = np.array([len(w) + 2 for w in ws], float)
    edges = a + (b - a) * np.concatenate([[0], np.cumsum(wl)]) / wl.sum()
    for i, w in enumerate(ws):
        words.append((w, edges[i], edges[i + 1], len(words) and 0))
groups = []                                 # blocos de até 3 palavras
i = 0
while i < len(words):
    n = 1
    while i + n < len(words) and n < 3 and sum(len(x[0]) for x in words[i:i + n + 1]) + n <= 17 \
            and not words[i + n - 1][0][-1] in "?!.,":
        n += 1
    groups.append(words[i:i + n]); i += n

# eventos da história
T_PIG_IN = phr[1][0]
T_MORPH0, T_MORPH1 = phr[2][0] + 0.9, phr[3][0] + 0.9
T_BOOM = phr[5][1] + 0.05
T_FUSE = T_BOOM - 1.3

# ---------------------------------------------------------------------- áudio
def mix_audio(path):
    n = int(TOTAL * SR)
    voice = np.zeros(n, np.float32)
    for c, (a, _) in zip(clips, phr):
        s = int(a * SR); voice[s:s + len(c)] += c
    voice /= max(0.01, np.abs(voice).max()) / 0.95
    rng = np.random.default_rng(1)
    tt = np.arange(n) / SR
    # música chiptune: baixo quadrado + arpejo
    bpm = 150; beat = 60 / bpm
    prog = [57, 53, 48, 55]                           # Am F C G (midi)
    music = np.zeros(n, np.float32)
    def sq(f, ph): return np.sign(np.sin(2 * np.pi * f * ph)) * 1.0
    step = beat / 2
    for k in range(int(TOTAL / step) + 1):
        ch = prog[(k // 8) % 4]
        s0, s1 = int(k * step * SR), min(n, int((k + 1) * step * SR))
        if s0 >= n: break
        ph = tt[s0:s1] - k * step
        env = np.exp(-ph * 9)
        bass = sq(440 * 2 ** ((ch - 12 - 69) / 12), tt[s0:s1]) * env * 0.5
        arp = [0, 4 if ch != 57 else 3, 7, 12][k % 4]
        lead = sq(440 * 2 ** ((ch + 12 + arp - 69) / 12), tt[s0:s1]) * np.exp(-ph * 14) * 0.35
        music[s0:s1] += (bass + lead).astype(np.float32)
    music *= 0.10
    # ducking simples quando há voz
    env = np.convolve(np.abs(voice), np.ones(2205) / 2205, "same")
    music *= (1 - 0.55 * np.clip(env * 6, 0, 1)).astype(np.float32)
    sfx = np.zeros(n, np.float32)
    def put(t0, x):
        s = int(t0 * SR); x = x[:max(0, n - s)]; sfx[s:s + len(x)] += x
    # "pop" ao entrar o porco e ao transformar
    for t0 in (T_PIG_IN, T_MORPH0):
        d = np.arange(int(0.18 * SR)) / SR
        put(t0, (np.sin(2 * np.pi * (300 + 900 * d / 0.18) * d) * np.exp(-d * 18) * 0.5).astype(np.float32))
    # sizzle do pavio (ruído agudo crescente)
    d = np.arange(int((T_BOOM - T_FUSE) * SR)) / SR
    noise = rng.standard_normal(len(d)).astype(np.float32)
    hp = noise - np.convolve(noise, np.ones(8) / 8, "same")
    put(T_FUSE, hp * (0.10 + 0.5 * (d / d[-1]) ** 2).astype(np.float32))
    # explosão
    d = np.arange(int(1.6 * SR)) / SR
    nz = rng.standard_normal(len(d)).astype(np.float32)
    lp = np.convolve(nz, np.ones(40) / 40, "same") * 3
    boom = (lp * np.exp(-d * 3.2) + np.sin(2 * np.pi * (90 - 50 * d) * d) * np.exp(-d * 4)) * 0.9
    put(T_BOOM, boom.astype(np.float32))
    # tique em cada bloco de legenda
    for g in groups:
        d = np.arange(int(0.05 * SR)) / SR
        put(g[0][1], (np.sin(2 * np.pi * 1500 * d) * np.exp(-d * 60) * 0.12).astype(np.float32))
    out = voice * 1.0 + music + sfx
    out = np.tanh(out * 1.1)
    out = (out / max(1e-6, np.abs(out).max()) * 0.92 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())

# ---------------------------------------------------------------------- cenário
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
rnd = random.Random(7)
NCOL = 4000
heights = [0]
for _ in range(NCOL):
    h = heights[-1]
    if rnd.random() < 0.22: h = min(2, max(0, h + rnd.choice((-1, 1))))
    heights.append(h)
BLK, GROUND = 16, 392
SPEED = 62.0                                # px/s (baixa resolução)
speckle = [[(rnd.randrange(BLK), rnd.randrange(BLK), rnd.choice((0, 1, 2))) for _ in range(7)] for _ in range(32)]
clouds = [(rnd.randrange(0, 600), rnd.randrange(30, 200), rnd.randrange(30, 60)) for _ in range(8)]

def surface(xw):
    """altura (y) do chão no mundo x, com degraus suavizados e pulinho."""
    c = xw / BLK
    i = int(math.floor(c)); f = c - i
    h0, h1 = heights[i], heights[i + 1]
    y0, y1 = GROUND - h0 * BLK, GROUND - h1 * BLK
    k = ease((f - 0.75) / 0.25) if h1 != h0 else 0
    y = y0 + (y1 - y0) * k
    hop = 9 * math.sin(math.pi * ease((f - 0.55) / 0.45)) if h1 != h0 else 0
    return y - hop * (1 if h1 >= h0 else 0.5)

def surf_flat(xw):                          # chão sem pulinho (para criaturas)
    i = int(math.floor(xw / BLK)); return GROUND - heights[min(i, NCOL)] * BLK

def draw_world(d, t, camx):
    # céu em degradê
    for y in range(0, GROUND, 4):
        k = y / GROUND
        d.rectangle([0, y, W, y + 4], fill=(int(95 + 90 * k), int(165 + 60 * k), int(235 + 15 * k)))
    d.rectangle([215, 20, 245, 50], fill=(255, 240, 150))              # sol quadrado
    for cx, cy, cw in clouds:
        x = (cx - t * 6) % 700 - 100
        d.rectangle([x, cy, x + cw, cy + 9], fill=(255, 255, 255))
        d.rectangle([x + 8, cy - 7, x + cw - 10, cy], fill=(255, 255, 255))
    c0 = int(camx // BLK) - 1
    for ci in range(c0, c0 + W // BLK + 3):
        x = ci * BLK - camx
        top = GROUND - heights[ci] * BLK
        d.rectangle([x, top, x + BLK, H], fill=(121, 85, 58))
        d.rectangle([x, top, x + BLK, top + 5], fill=(98, 174, 62))
        d.rectangle([x, top, x + BLK, top + 1], fill=(130, 205, 80))
        for (sx, sy, kind) in speckle[ci % 32]:
            yy = top + 6 + sy * 0.9 + (H - top) * 0 
            col = [(97, 66, 44), (140, 100, 70), (110, 110, 110)][kind]
            d.rectangle([x + sx, yy, x + sx + 2, yy + 2], fill=col)
        # camadas mais fundas viram pedra
        for yy in range(int(top) + 48, H, BLK):
            d.rectangle([x, yy, x + BLK, H], fill=(115, 115, 118))
            break
        d.line([x, top, x, H], fill=(0, 0, 0, 40), width=1)
    # linhas de bloco no chão
    for yy in range(GROUND - 2 * BLK, H, BLK):
        d.line([0, yy + 1, W, yy + 1], fill=(0, 0, 0), width=1) if False else None

# ----------------------------------------------------------- sprites (px baixo)
def rect(d, x, y, w, h, c): d.rectangle([x, y, x + w - 1, y + h - 1], fill=c)

def make_steve(frame):
    im = Image.new("RGBA", (16, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sw = int(math.sin(frame * 0.9) * 3)
    rect(d, 4, 12, 4, 12, (60, 60, 150)); rect(d, 8, 12, 4, 12, (50, 50, 130))   # (placeholder, redesenhado abaixo)
    im = Image.new("RGBA", (16, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rect(d, 4 - sw, 22, 4, 10, (70, 60, 160)); rect(d, 8 + sw, 22, 4, 10, (55, 48, 130))   # pernas
    rect(d, 4, 10, 8, 12, (0, 170, 190))                                                   # torso
    rect(d, 6 - sw, 10, 3, 11, (228, 170, 130)); rect(d, 7 + sw, 10, 3, 11, (200, 148, 112))  # braços
    rect(d, 4, 2, 8, 8, (228, 170, 130)); rect(d, 4, 2, 8, 3, (80, 52, 30))                # cabeça + cabelo
    rect(d, 5, 6, 2, 2, (255, 255, 255)); rect(d, 6, 6, 1, 2, (60, 60, 200))
    rect(d, 9, 6, 2, 2, (255, 255, 255)); rect(d, 10, 6, 1, 2, (60, 60, 200))
    rect(d, 6, 8, 4, 1, (130, 80, 60))
    return im

def make_creeper(frame, flash=0.0):
    im = Image.new("RGBA", (16, 28), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    g = random.Random(3)
    base = (84, 190, 70)
    sw = int(math.sin(frame * 0.9) * 1)
    for (x, y, w, h) in [(2 - sw, 21, 5, 7), (9 + sw, 21, 5, 7)]:
        rect(d, x, y, w, h, (60, 150, 52))
    rect(d, 4, 10, 8, 13, (72, 165, 60)); rect(d, 1, 21, 4, 7, (66, 158, 56)); rect(d, 11, 21, 4, 7, (66, 158, 56))
    rect(d, 3, 0, 10, 10, base)
    for _ in range(26):
        rect(d, 3 + g.randrange(10), g.randrange(10), 2, 2, g.choice(((58, 140, 50), (110, 215, 90))))
    rect(d, 4, 2, 3, 3, (15, 30, 15)); rect(d, 9, 2, 3, 3, (15, 30, 15))
    rect(d, 7, 5, 2, 5, (15, 30, 15)); rect(d, 6, 7, 4, 3, (15, 30, 15))
    if flash > 0:
        w = Image.new("RGBA", im.size, (255, 255, 255, int(255 * flash)))
        w.putalpha(Image.composite(w.getchannel("A"), Image.new("L", im.size, 0), im.getchannel("A")))
        im = Image.alpha_composite(im, w)
    return im

def make_pig(frame):
    im = Image.new("RGBA", (28, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sw = int(math.sin(frame * 1.1) * 2)
    for x in (4, 20):
        rect(d, x + sw, 12, 4, 6, (230, 140, 150)); rect(d, x - sw + 4 - 4, 12, 4, 6, (214, 124, 136)) if False else None
    rect(d, 3, 4, 20, 10, (245, 160, 170))
    rect(d, 20, 3, 8, 9, (245, 160, 170)); rect(d, 25, 7, 3, 4, (232, 126, 140))
    rect(d, 22, 5, 2, 2, (30, 30, 30)); rect(d, 26, 8, 1, 1, (140, 60, 70))
    for x in (2, 8, 16, 21):
        rect(d, x + (sw if x in (2, 16) else -sw), 13, 3, 5, (232, 130, 142))
    return im

def paste_scaled(base, sprite, x, y, sx=1.0, sy=1.0, anchor="bottom"):
    w, h = max(1, int(sprite.width * sx)), max(1, int(sprite.height * sy))
    sp = sprite.resize((w, h), Image.NEAREST)
    base.alpha_composite(sp, (int(x - w / 2), int(y - h)))

# --------------------------------------------------------------------- texto
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(sz): return ImageFont.truetype(FONT_B, sz)
def text_stroke(d, xy, s, f, fill, stroke=9, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)

def draw_caption(d, t):
    g = None
    for grp in groups:
        if grp[0][1] - 0.02 <= t < grp[-1][2] + 0.10: g = grp; break
    if g is None: return
    size = 118
    while True:
        f = font(size)
        ws = [d.textlength(w[0], font=f) for w in g]
        sp = d.textlength(" ", font=f)
        tot = sum(ws) + sp * (len(g) - 1)
        if tot <= 960 or size < 50: break
        size -= 6
    x = FW / 2 - tot / 2; y = 1030
    for (w, a, b, _), wd in zip(g, ws):
        active = a <= t < b
        pop = 1.0
        if active: pop = 1 + 0.16 * math.sin(math.pi * min(1, (t - a) / 0.14)) if t - a < 0.14 else 1.0
        fs = int(size * pop)
        col = (255, 226, 40) if active else (255, 255, 255)
        text_stroke(d, (x + wd / 2, y + (0 if not active else -4)), w, font(fs), col, stroke=max(8, size // 11))
        x += wd + sp

def draw_ui(img, t):
    d = ImageDraw.Draw(img)
    # selo do topo
    if int(t * 2) % 2 == 0 or t > 1.5:
        pass
    d.rounded_rectangle([110, 330, FW - 110, 440], radius=24, fill=(30, 140, 50), outline=(0, 0, 0), width=8)
    d.text((FW / 2, 385), "CURIOSIDADE MINECRAFT", font=font(50), fill=(255, 255, 255), anchor="mm")
    # título gigante nos primeiros segundos
    if t < phr[0][1]:
        k = ease(t / 0.25)
        text_stroke(d, (FW / 2, 560), "CREEPER", font(int(150 * (0.7 + 0.3 * k))), (120, 255, 90), stroke=14)
        text_stroke(d, (FW / 2, 720), "= ERRO?!", font(int(130 * (0.7 + 0.3 * k))), (255, 226, 40), stroke=14)
    # barra de progresso
    d.rectangle([0, FH - 26, FW, FH], fill=(0, 0, 0))
    d.rectangle([0, FH - 26, int(FW * t / TOTAL), FH], fill=(120, 255, 90))
    # CTA final
    if t >= phr[6][0]:
        k = ease((t - phr[6][0]) / 0.3)
        sc = 1 + 0.05 * math.sin(t * 8)
        d.rounded_rectangle([FW / 2 - 400 * k, 1290 - 90 * k, FW / 2 + 400 * k, 1290 + 90 * k], radius=30,
                            fill=(255, 40, 40), outline=(0, 0, 0), width=10)
        if k > 0.8:
            d.text((FW / 2, 1290), "SEGUIR  +  CURTIR", font=font(int(70 * sc)), fill=(255, 255, 255), anchor="mm")

# --------------------------------------------------------------------- frames
def render(fi):
    t = fi / FPS
    camx = t * SPEED
    shake = 0
    if T_BOOM <= t < T_BOOM + 0.7:
        a = 1 - (t - T_BOOM) / 0.7
        shake = a * 7
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(base)
    draw_world(d, t, camx)
    frame = fi
    sx_steve = 55
    exploded = t >= T_BOOM
    steve_y = surface(camx + sx_steve)
    # Steve
    if not exploded:
        paste_scaled(base, make_steve(frame // 2), sx_steve, steve_y, 2.2, 2.2)
    else:
        k = t - T_BOOM
        if k < 1.2:
            sp = make_steve(0).rotate(k * 700, expand=True)
            base.alpha_composite(sp.resize((sp.width * 2, sp.height * 2), Image.NEAREST), (int(sx_steve + k * 90), int(steve_y - 60 - k * 260 + 420 * k * k)))
    # porco / creeper
    px = None
    if t >= T_PIG_IN and not exploded:
        walk = ease((t - T_PIG_IN) / 0.9)
        px = 300 + (190 - 300) * walk
        if t > T_FUSE - 0.6:                                 # creeper se aproxima
            px = 190 - 70 * ease((t - (T_FUSE - 0.6)) / 1.5)
        py = surf_flat(camx + px)
        m = ease((t - T_MORPH0) / (T_MORPH1 - T_MORPH0))
        pig, cre = make_pig(frame // 2), make_creeper(frame // 2)
        if t < T_MORPH0:
            paste_scaled(base, pig, px, py, 3, 3)
        else:
            wob = 1 + 0.12 * math.sin(m * math.pi * 6) * (1 - m)
            pigs = pig.resize((int(28 * 3 * (1 - 0.45 * m)), int(18 * 3 * (1 + 1.55 * m))), Image.NEAREST)
            pigs.putalpha(pigs.getchannel("A").point(lambda v: int(v * (1 - m))))
            cr = cre.resize((int(16 * 3.4), int(28 * 3.4 * wob)), Image.NEAREST)
            cr.putalpha(cr.getchannel("A").point(lambda v: int(v * m)))
            flash = 0.0
            if t > T_FUSE:
                flash = 0.5 + 0.5 * math.sin((t - T_FUSE) * 22)
                sw = 1 + 0.35 * ease((t - T_FUSE) / (T_BOOM - T_FUSE))
                cre2 = make_creeper(frame // 2, flash).resize((int(16 * 3.4 * sw), int(28 * 3.4 * sw)), Image.NEAREST)
                cr = cre2
            base.alpha_composite(pigs, (int(px - pigs.width / 2), int(py - pigs.height)))
            base.alpha_composite(cr, (int(px - cr.width / 2), int(py - cr.height)))
    # explosão
    if exploded:
        k = t - T_BOOM
        ex, ey = 120, surf_flat(camx + 120) - 50
        r = random.Random(11)
        for _ in range(70):
            ang, spd, sz = r.uniform(0, 2 * math.pi), r.uniform(40, 230), r.randrange(3, 9)
            if k < 0.9:
                x = ex + math.cos(ang) * spd * k * 1.2
                y = ey + math.sin(ang) * spd * k * 1.2 + 140 * k * k
                col = r.choice(((255, 255, 255), (255, 210, 60), (255, 120, 30), (90, 90, 90), (60, 180, 60)))
                d2 = ImageDraw.Draw(base); d2.rectangle([x, y, x + sz, y + sz], fill=col)
        if k < 0.25:
            ov = Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - k / 0.25))))
            base.alpha_composite(ov)
    if shake:
        base = base.transform(base.size, Image.AFFINE, (1, 0, random.uniform(-shake, shake), 0, 1, random.uniform(-shake, shake)))
    big = base.resize((FW, FH), Image.NEAREST).convert("RGB")
    draw_ui(big, t)
    draw_caption(ImageDraw.Draw(big), t)
    return big

def main():
    wav = os.path.splitext(OUT)[0] + "_audio.wav"
    mix_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FW}x{FH}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
           "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(NF):
        p.stdin.write(render(fi).tobytes())
    p.stdin.close(); p.wait()
    os.remove(wav)
    print(f"ok: {OUT} ({TOTAL:.1f}s, {NF} frames)")

if __name__ == "__main__":
    main()

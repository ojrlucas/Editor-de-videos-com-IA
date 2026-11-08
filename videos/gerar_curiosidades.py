#!/usr/bin/env python3
"""Short 9:16 de 25 s: 3 curiosidades do Minecraft com imagens REAIS do jogo animadas.

- Imagens: texturas reais do Minecraft (ver baixar_assets.sh), recortadas/montadas sem fundo.
- Efeitos: pop, brilho, glitch, partículas, selos. Legendas palavra a palavra. Sem música de fundo.
- Voz (VOZ=...): kokoro (neural offline, pt-BR), google (Cloud TTS, precisa GOOGLE_TTS_KEY),
  arquivo:<pasta> (frase_0.wav ... gravadas por você) ou espeak (robótica, só reserva).
Uso: [VOZ=kokoro] python3 gerar_curiosidades.py [saida.mp4]
"""
import ctypes, math, random, subprocess, sys, wave, os, base64, json, io, tempfile, urllib.request
import numpy as np
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

# ------------------------------------------------------------------------- voz
def _resample(a, sr):
    return a.astype(np.float32) if sr == SR else np.interp(
        np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype(np.float32)

def _trim(a):
    idx = np.where(np.abs(a) > 0.01)[0]
    return a[idx[0]:idx[-1] + 1]

def _read_wav(data):
    with wave.open(io.BytesIO(data)) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() > 1: x = x.reshape(-1, w.getnchannels()).mean(1)
    return x, sr

def synth_espeak():                       # reserva robótica
    import espeakng_loader
    lib = ctypes.CDLL(espeakng_loader.get_library_path()); lib.espeak_Initialize.restype = ctypes.c_int
    rate = lib.espeak_Initialize(1, 0, espeakng_loader.get_data_path().encode(), 0)
    buf = []; CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
    def cb(wav, n, ev):
        if wav and n > 0: buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
        return 0
    keep = CB(cb); lib.espeak_SetSynthCallback(keep); lib.espeak_SetVoiceByName(b"pt-br")
    lib.espeak_SetParameter(1, 175, 0); lib.espeak_SetParameter(3, 38, 0); out = []
    for fala, _ in SCRIPT:
        buf.clear(); b = fala.encode()
        lib.espeak_Synth(b, len(b) + 1, 0, 1, 0, 1, None, None); lib.espeak_Synchronize()
        out.append(_resample(_trim(np.concatenate(buf).astype(np.float32) / 32768.0), rate))
    return out

def synth_kokoro():                       # voz neural offline (modelo ~300 MB, ver README)
    from kokoro_onnx import Kokoro
    d = os.environ.get("KOKORO_DIR", "/tmp/kokoro")
    k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    voz = os.environ.get("KOKORO_VOICE", "pm_alex")     # pm_alex / pm_santa (masc.), pf_dora (fem.)
    out = []
    for fala, _ in SCRIPT:
        x, sr = k.create(fala, voice=voz, speed=1.0, lang="pt-br")
        out.append(_resample(_trim(np.asarray(x, np.float32)), sr))
    return out

def synth_google():                       # Google Cloud Text-to-Speech (REST)
    key = os.environ["GOOGLE_TTS_KEY"]; out = []
    voz = os.environ.get("GOOGLE_VOICE", "pt-BR-Neural2-B")
    for fala, _ in SCRIPT:
        body = json.dumps({"input": {"text": fala}, "voice": {"languageCode": "pt-BR", "name": voz},
                           "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}).encode()
        rq = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize?key=" + key, body,
                                    {"Content-Type": "application/json"})
        x, sr = _read_wav(base64.b64decode(json.load(urllib.request.urlopen(rq))["audioContent"]))
        out.append(_resample(_trim(x), sr))
    return out

def synth_arquivos(pasta):                # sua própria voz: frase_0.wav ... frase_4.wav
    out = []
    for i in range(len(SCRIPT)):
        x, sr = _read_wav(open(os.path.join(pasta, f"frase_{i}.wav"), "rb").read())
        out.append(_resample(_trim(x), sr))
    return out

def atempo(a, f):                         # acelera/desacelera sem mudar o tom
    with tempfile.TemporaryDirectory() as td:
        i, o = os.path.join(td, "i.wav"), os.path.join(td, "o.wav")
        with wave.open(i, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", i, "-af", f"atempo={f:.4f}", o], check=True)
        x, sr = _read_wav(open(o, "rb").read())
    return x

VOZ = os.environ.get("VOZ", "espeak")
if VOZ == "kokoro": clips = synth_kokoro()
elif VOZ == "google": clips = synth_google()
elif VOZ.startswith("arquivo:"): clips = synth_arquivos(VOZ.split(":", 1)[1])
else: clips = synth_espeak()

T0, VOICE_END = 0.3, 23.6
speech = sum(len(c) for c in clips) / SR
budget = VOICE_END - T0 - 0.2 * (len(clips) - 1)         # no mínimo 0,2 s de pausa entre frases
if speech > budget:                                       # cabe nos 25 s acelerando levemente
    f = speech / budget
    assert f < 1.45, f"fala longa demais ({speech:.1f}s); encurte o roteiro"
    clips = [atempo(c, f) for c in clips]; speech = sum(len(c) for c in clips) / SR
GAP = min(0.6, (VOICE_END - T0 - speech) / (len(clips) - 1))
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
    # sem música de fundo: apenas voz + efeitos sonoros discretos
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
    out = np.tanh((voice + sfx * 0.5) * 1.1)
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
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "minecraft")
def tex(name):
    f = os.path.join(ASSETS, name)
    if not os.path.exists(f): sys.exit("texturas ausentes: rode ./baixar_assets.sh")
    return Image.open(f).convert("RGBA")

def crop(im, x, y, w, h): return im.crop((x, y, x + w, y + h))

def build_creeper():                      # vista frontal montada a partir da skin real
    k = tex("skin_creeper.png"); im = Image.new("RGBA", (8, 26), (0, 0, 0, 0))
    im.paste(crop(k, 8, 8, 8, 8), (0, 0)); im.paste(crop(k, 20, 20, 8, 12), (0, 8))
    im.paste(crop(k, 4, 20, 4, 6), (0, 20)); im.paste(crop(k, 4, 20, 4, 6), (4, 20))
    return im

def build_enderman():
    k = tex("skin_enderman.png"); e = tex("skin_enderman_eyes.png"); im = Image.new("RGBA", (12, 46), (0, 0, 0, 0))
    d = ImageDraw.Draw(im); dark = (14, 14, 18, 255)          # fundo escuro sob as texturas (a skin tem pixels vazados)
    for box in ((2, 0, 9, 7), (2, 8, 9, 19), (0, 8, 1, 37), (10, 8, 11, 37), (3, 20, 4, 45), (7, 20, 8, 45)):
        d.rectangle(box, fill=dark)
    head = crop(k, 8, 8, 8, 8); head.alpha_composite(crop(e, 8, 8, 8, 8))
    for part, pos in ((head, (2, 0)), (crop(k, 20, 20, 8, 12), (2, 8)), (crop(k, 58, 2, 2, 30), (0, 8)),
                      (crop(k, 58, 2, 2, 30), (10, 8)), (crop(k, 58, 2, 2, 26), (3, 20)), (crop(k, 58, 2, 2, 26), (7, 20))):
        im.alpha_composite(part, pos)
    return im

def build_pig_head():
    k = tex("skin_pig.png"); im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    im.paste(crop(k, 8, 8, 8, 8), (0, 0)); im.paste(crop(k, 17, 17, 4, 3), (2, 4))
    return im

def _face(texim, O, u, v, size):
    """projeta a textura num paralelogramo (O + u*x/16 + v*y/16) sem suavização."""
    M = np.array([[u[0], v[0]], [u[1], v[1]]], float) / texim.width
    Mi = np.linalg.inv(M)
    c = -Mi @ np.array(O, float)
    return texim.transform(size, Image.AFFINE, (Mi[0, 0], Mi[0, 1], c[0], Mi[1, 0], Mi[1, 1], c[1]), Image.NEAREST)

def build_grass_cube(sz=480):
    top = tex("block_grass_block_top.png"); side = tex("block_grass_block_side.png")
    r, g, b, a = top.split()                                   # a textura do topo é cinza: aplica cor de bioma
    top = Image.merge("RGBA", (r.point(lambda v: v * 124 // 255), g.point(lambda v: v * 189 // 255),
                               b.point(lambda v: v * 107 // 255), a))
    # a lateral real tem a franja de grama cinza no overlay: pinta a franja verde onde o pixel é cinza claro
    px = side.load()
    for y in range(side.height):
        for x in range(side.width):
            R, G, B, A = px[x, y]
            if abs(R - G) < 6 and abs(G - B) < 6 and R > 90:
                px[x, y] = (R * 124 // 255 + 20, G * 189 // 255 + 20, B * 107 // 255, A)
    e = sz / 2 * 0.5
    ex, ey, ez = (sz * 0.433, sz * 0.25), (-sz * 0.433, sz * 0.25), (0, sz * 0.5)
    P0 = (sz * 0.433, 0); P3 = (P0[0] + ey[0], P0[1] + ey[1]); P1 = (P0[0] + ex[0], P0[1] + ex[1])
    P2 = (P0[0] + ex[0] + ey[0], P0[1] + ex[1] + ey[1])
    size = (int(sz * 0.866) + 1, int(sz * 0.5 + sz * 0.5) + 2)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    left = _face(side, P3, ex, ez, size); right = _face(side, P2, (-ey[0], -ey[1]), ez, size)
    topf = _face(top, P0, ex, ey, size)
    for im, k in ((left, 0.85), (right, 0.62)):
        r, g, b, a = im.split(); im = Image.merge("RGBA", (r.point(lambda v: int(v * k)), g.point(lambda v: int(v * k)), b.point(lambda v: int(v * k)), a))
        out.alpha_composite(im)
    out.alpha_composite(topf)
    return out

SP = dict(grass=build_grass_cube(), pig=build_pig_head(), creeper=build_creeper(), ender=build_enderman(),
          diamond=tex("item_diamond.png"), coin=tex("item_gold_ingot.png"), emerald=tex("item_emerald.png"),
          gunpowder=tex("item_gunpowder.png"), pearl=tex("item_ender_pearl.png"), eye=tex("item_ender_eye.png"),
          ore=tex("block_diamond_ore.png"))

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

def orbit(big, t, cx, cy, rx, ry, items, size, glow=None, vis=1.0, speed=1.4):
    n = len(items)
    for j, it in enumerate(items):
        ang = t * speed + j * 2 * math.pi / n
        place(big, SP[it], cx + math.cos(ang) * rx, cy + math.sin(ang) * ry, size * (0.8 + 0.2 * math.sin(ang)),
              rot=math.sin(t * 3 + j) * 12, alpha=vis, glow=glow, gi=.6)

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
            place(big, SP["pig"], CX, CY + 40 + bob * .5, 420, sx=appear, sy=appear, glow=(255, 150, 190), gi=.7)
        elif t < T_MORPH + 0.5:
            k = ease((t - pre) / 0.6); amt = 1.5 if t < T_MORPH else 1.5 * (1 - (t - T_MORPH) / 0.5)
            src = SP["pig"] if t < T_MORPH else SP["creeper"]
            h = 420 if t < T_MORPH else 640
            g = glitch(src, amt, rng)
            # "alongando" altura/largura durante a transição
            sx_, sy_ = (1 - 0.35 * k, 1 + 0.5 * k) if t < T_MORPH else (1, 1)
            place(big, g, CX + rng.randint(-14, 14) * (amt > .3), CY + (40 if t < T_MORPH else 0), h, sx=sx_, sy=sy_,
                  glow=(120, 255, 100), gi=.9 * k)
        else:
            place(big, SP["creeper"], CX, CY + bob * .6, 640, sx=1 + .03 * math.sin(t * 6), sy=1,
                  glow=(120, 255, 100), gi=.9)
        if t > T_MORPH + 0.4: orbit(big, t, CX, CY - 40, 330, 120, ["gunpowder", "gunpowder", "gunpowder"], 130, glow=(160, 160, 160), vis=out)
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
        place(big, SP["ender"], pos, CY + 30 + bob * .3, 780, sx=appear, sy=appear, alpha=vis, glow=(210, 90, 255),
              gi=0.55 + 0.3 * (math.sin(t * 9) > 0))
        orbit(big, t, pos, CY + 30, 340, 130, ["eye", "pearl"], 130, glow=(220, 90, 255), vis=appear * out)
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
        orbit(big, t, CX, CY, 360, 120, ["emerald", "ore"], 130, glow=(80, 255, 160), vis=appear, speed=-1.2)
        # chuva de moedas
        for n in range(22):
            r = random.Random(100 + n); t0 = T_COINS + r.uniform(0, 1.6); x = r.randrange(80, FW - 80)
            k = t - t0
            if 0 <= k < 2.2:
                y = -60 + k * 900 + 0
                wscale = abs(math.cos(k * 9 + n))
                place(big, SP["coin"], x, y, 110, rot=k * 260 + n * 40, glow=(255, 200, 40), gi=.4)
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
    print(f"ok: {OUT} ({DURATION}s, {NF} frames, voz {VOZ}, fala termina em {phr[-1][1]:.1f}s)")

if __name__ == "__main__":
    main()

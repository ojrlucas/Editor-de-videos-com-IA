#!/usr/bin/env python3
"""Short 9:16 de 25 s: "4 fatos do Minecraft que quase ninguém sabe" (2025-2026).

Todos os fatos foram conferidos na Minecraft Wiki / Minecraft.net (ver FATOS.md).
Imagens: texturas reais do jogo (./baixar_assets.sh). Sem música de fundo.
Voz (VOZ=...): kokoro (neural offline pt-BR), google (Cloud TTS, GOOGLE_TTS_KEY),
arquivo:<pasta> (frase_0.wav ... sua própria gravação) ou espeak (robótica, só reserva).
Uso: [VOZ=kokoro] python3 gerar_fatos.py [saida.mp4]
"""
import ctypes, math, random, subprocess, sys, wave, os, base64, json, io, tempfile, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "fatos_minecraft_2026.mp4"
FPS, W, H, S = 30, 270, 480, 4
FW, FH = W * S, H * S
SR = 44100
DURATION = 25.0
NF = int(DURATION * FPS)

# (fala, legenda) — cada item é uma cena
SCRIPT = [
    ("Quatro fatos do Minecraft que quase ninguém sabe!",
     "4 FATOS DO MINECRAFT QUE QUASE NINGUÉM SABE!"),
    ("A golden dandelion faz filhotes pararem de crescer. Usada de novo, eles voltam a crescer.",
     "A GOLDEN DANDELION FAZ FILHOTES PARAREM DE CRESCER. USADA DE NOVO, ELES VOLTAM A CRESCER."),
    ("O som do Creaking foi feito com pretzel, cadeira rangendo e dedos estalando.",
     "O SOM DO CREAKING FOI FEITO COM PRETZEL, CADEIRA RANGENDO E DEDOS ESTALANDO."),
    ("O golem de cobre perdeu a votação de mobs e só entrou no jogo anos depois.",
     "O GOLEM DE COBRE PERDEU A VOTAÇÃO DE MOBS E SÓ ENTROU NO JOGO ANOS DEPOIS."),
    ("O ghast seco? A própria Mojang brinca que ainda investiga: restos, ovo ou outra coisa.",
     "O GHAST SECO? A PRÓPRIA MOJANG BRINCA QUE AINDA INVESTIGA: RESTOS, OVO OU OUTRA COISA."),
    ("Segue pra mais fatos!", "SEGUE PRA MAIS FATOS!"),
]
TITLES = ["", "GOLDEN DANDELION", "CREAKING", "GOLEM DE COBRE", "GHAST SECO", ""]
SOURCES = ["",
           "FONTE: MINECRAFT WIKI · JAVA 26.1 (24/03/2026)",
           "FONTE: MINECRAFT WIKI · MINECRAFT LIVE 2024",
           "FONTE: MINECRAFT WIKI · COPPER GOLEM",
           "FONTE: MINECRAFT.NET · MOB MENAGERIE (09/04/2026)",
           ""]
ACCENT = [(90, 230, 255), (255, 214, 64), (255, 160, 70), (240, 140, 100), (200, 130, 255), (90, 230, 255)]

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

def synth_espeak():
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

def animar(a, pitch=1.07):
    """deixa a voz mais animada: tom um pouco mais agudo (sem mudar o ritmo), compressão e brilho nos agudos."""
    with tempfile.TemporaryDirectory() as td:
        i, o = os.path.join(td, "i.wav"), os.path.join(td, "o.wav")
        with wave.open(i, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
        af = (f"asetrate={SR * pitch:.0f},aresample={SR},atempo={1 / pitch:.4f},"
              "equalizer=f=3200:t=q:w=1.2:g=4,equalizer=f=180:t=q:w=1:g=-2,"
              "acompressor=threshold=-24dB:ratio=3:attack=5:release=80:makeup=5")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", i, "-af", af, o], check=True)
        x, _ = _read_wav(open(o, "rb").read())
    return x

def synth_kokoro():
    from kokoro_onnx import Kokoro
    d = os.environ.get("KOKORO_DIR", "/tmp/kokoro")
    k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    voz = os.environ.get("KOKORO_VOICE", "pm_alex")      # pm_alex / pm_santa (masc.), pf_dora (fem.)
    vel = float(os.environ.get("KOKORO_SPEED", "1.0")); alegre = os.environ.get("ANIMAR", "0") == "1"
    out = []
    for fala, _ in SCRIPT:
        x, sr = k.create(fala, voice=voz, speed=vel, lang="pt-br")
        x = _resample(_trim(np.asarray(x, np.float32)), sr)
        out.append(_trim(animar(x)) if alegre else x)
    return out

def synth_google():
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

def synth_arquivos(pasta):
    """lê frase_0 ... frase_5 (wav/mp3/m4a/ogg/aac/flac), limpa ruído e nivela o volume com ffmpeg."""
    out = []
    for i in range(len(SCRIPT)):
        achados = [f for f in sorted(os.listdir(pasta)) if os.path.splitext(f)[0] == f"frase_{i}"]
        if not achados: sys.exit(f"faltou o arquivo frase_{i}.* em {pasta}")
        with tempfile.TemporaryDirectory() as td:
            o = os.path.join(td, "o.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(pasta, achados[0]), "-ac", "1",
                            "-ar", str(SR), "-af", "highpass=f=80,afftdn=nf=-30,loudnorm=I=-18:TP=-2:LRA=7", o], check=True)
            x, sr = _read_wav(open(o, "rb").read())
        out.append(_resample(_trim(x), sr))
    return out

def atempo(a, f):                          # muda a velocidade sem mudar o tom
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

T0, VOICE_END = 0.25, 23.9
speech = sum(len(c) for c in clips) / SR
budget = VOICE_END - T0 - 0.18 * (len(clips) - 1)
if speech > budget:
    f = speech / budget
    assert f < 1.5, f"fala longa demais ({speech:.1f}s); encurte o roteiro"
    clips = [atempo(c, f) for c in clips]; speech = sum(len(c) for c in clips) / SR
GAP = min(0.5, (VOICE_END - T0 - speech) / (len(clips) - 1))
phr, t = [], T0
for c in clips:
    d = len(c) / SR; phr.append((t, t + d)); t += d + GAP
assert phr[-1][1] < DURATION - 0.3, "fala não coube em 25 s"
TOTAL = DURATION
starts = [p[0] if i else 0.0 for i, p in enumerate(phr)]
ends = [starts[i + 1] if i + 1 < len(starts) else DURATION for i in range(len(starts))]

WT = []                                    # por cena: [(palavra, ini, fim)]
for (_, cap), (a, b) in zip(SCRIPT, phr):
    ws = cap.split(); wl = np.array([len(w) + 2 for w in ws], float)
    e = a + (b - a) * np.concatenate([[0], np.cumsum(wl)]) / wl.sum()
    WT.append([(w, e[i], e[i + 1]) for i, w in enumerate(ws)])

def kw(scene, prefix):                     # instante em que uma palavra da legenda começa
    for w, a, b in WT[scene]:
        if w.startswith(prefix): return a
    raise KeyError(prefix)

# ---------------------------------------------------------------------- áudio
def mix_audio(path):
    n = int(TOTAL * SR); rng = np.random.default_rng(4)
    voice = np.zeros(n, np.float32)
    for c, (a, _) in zip(clips, phr):
        s = int(a * SR); voice[s:s + len(c)] += c
    voice /= max(0.01, np.abs(voice).max()) / 0.95
    sfx = np.zeros(n, np.float32)
    def put(t0, x):
        s = int(t0 * SR); x = x[:max(0, n - s)]
        if s >= 0: sfx[s:s + len(x)] += x
    def sweep(f0, f1, dur, vol, decay=10):
        d = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * (f0 + (f1 - f0) * d / dur) * d) * np.exp(-d * decay) * vol).astype(np.float32)
    def crack(vol=0.6):
        d = np.arange(int(0.12 * SR)) / SR; z = rng.standard_normal(len(d)).astype(np.float32)
        return ((z - np.convolve(z, np.ones(6) / 6, "same")) * np.exp(-d * 45) * vol).astype(np.float32)
    for i in range(1, len(starts)): put(starts[i], sweep(160, 45, 0.28, 0.9, 9)); put(starts[i], crack(0.3))   # impacto de cada cena
    put(0.05, sweep(160, 45, 0.28, 0.9, 9))
    put(kw(1, "PARAREM"), sweep(900, 200, 0.35, 0.5, 7)); put(kw(1, "USADA"), sweep(300, 1100, 0.3, 0.5, 8))
    for p in ("PRETZEL", "CADEIRA", "DEDOS"): put(kw(2, p), crack(0.9))
    put(kw(3, "PERDEU"), sweep(700, 150, 0.4, 0.55, 6))
    for k, f in enumerate((523, 659, 784, 1047)): put(kw(3, "ENTROU") + 0.09 * k, sweep(f, f, 0.18, 0.4, 9))
    for p in ("RESTOS", "OVO", "OUTRA"): put(kw(4, p), sweep(420, 380, 0.3, 0.35, 6))
    put(starts[5] + 0.05, sweep(1200, 1200, 0.25, 0.3, 8))
    out = np.tanh((voice + sfx * 0.45) * 1.1)                # só voz + efeitos: sem música de fundo
    out = (out / max(1e-6, np.abs(out).max()) * 0.92 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())

# ------------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def back(x):
    x = clamp(x); c1 = 2.2; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def bounce(x):
    x = clamp(x); n1, d1 = 7.5625, 2.75
    if x < 1 / d1: return n1 * x * x
    if x < 2 / d1: x -= 1.5 / d1; return n1 * x * x + 0.75
    if x < 2.5 / d1: x -= 2.25 / d1; return n1 * x * x + 0.9375
    x -= 2.625 / d1; return n1 * x * x + 0.984375

# ----------------------------------------------------------------------- sprites
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "minecraft")
def tex(name):
    f = os.path.join(ASSETS, name)
    if not os.path.exists(f): sys.exit("texturas ausentes: rode ./baixar_assets.sh")
    return Image.open(f).convert("RGBA")

def _face(texim, O, u, v, size):
    M = np.array([[u[0], v[0]], [u[1], v[1]]], float) / texim.width
    Mi = np.linalg.inv(M); c = -Mi @ np.array(O, float)
    return texim.transform(size, Image.AFFINE, (Mi[0, 0], Mi[0, 1], c[0], Mi[1, 0], Mi[1, 1], c[1]), Image.NEAREST)

def build_iso(top, left, right, sz=480, dark=(0.85, 0.62)):
    ex, ey, ez = (sz * 0.433, sz * 0.25), (-sz * 0.433, sz * 0.25), (0, sz * 0.5)
    P0 = (sz * 0.433, 0); P3 = (P0[0] + ey[0], P0[1] + ey[1]); P2 = (P0[0] + ex[0] + ey[0], P0[1] + ex[1] + ey[1])
    size = (int(sz * 0.866) + 1, int(sz) + 2); out = Image.new("RGBA", size, (0, 0, 0, 0))
    for im, k in ((_face(left, P3, ex, ez, size), dark[0]), (_face(right, P2, (-ey[0], -ey[1]), ez, size), dark[1])):
        r, g, b, a = im.split()
        out.alpha_composite(Image.merge("RGBA", tuple(c.point(lambda v: int(v * k)) for c in (r, g, b)) + (a,)))
    out.alpha_composite(_face(top, P0, ex, ey, size))
    return out

def build_pig_head():
    k = tex("skin_pig.png"); im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    im.paste(k.crop((8, 8, 16, 16)), (0, 0)); im.paste(k.crop((17, 17, 21, 20)), (2, 4))
    return im

SP = dict(
    dandelion=tex("block_golden_dandelion.png"), heart=tex("block_creaking_heart.png"),
    egg_creaking=tex("egg_creaking.png"), egg_golem=tex("egg_copper_golem.png"),
    egg_ghast=tex("egg_happy_ghast.png"), egg_allay=tex("egg_allay.png"),
    ghast=build_iso(tex("dried_ghast_top.png"), tex("dried_ghast_north.png"), tex("dried_ghast_east.png")),
    baby=build_pig_head(),
    cu=[tex("block_copper_block.png"), tex("block_exposed_copper.png"),
        tex("block_weathered_copper.png"), tex("block_oxidized_copper.png")],
)

# ------------------------------------------------------------------ composição
def place(big, spr, cx, cy, h, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, glow=None, gi=0.9):
    w = max(2, int(spr.width / spr.height * h * sx)); hh = max(2, int(h * sy))
    s = spr.resize((w, hh), Image.NEAREST)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1: s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    if glow and alpha > 0.02:
        pad = 70; lay = Image.new("RGBA", (s.width + 2 * pad, s.height + 2 * pad), (0, 0, 0, 0))
        m = Image.new("L", lay.size, 0); m.paste(s.getchannel("A"), (pad, pad))
        m = m.filter(ImageFilter.GaussianBlur(28)).point(lambda v: min(255, int(v * 2.0 * gi * alpha)))
        lay.paste(Image.new("RGBA", lay.size, glow + (255,)), (0, 0), m)
        big.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)
    big.paste(s, (int(cx - s.width / 2), int(cy - s.height / 2)), s)

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fc = {}
def font(sz):
    sz = max(8, int(sz))
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FONT_B, sz)
    return _fc[sz]

def tstroke(d, xy, s, f, fill, stroke=9, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)

def sticker(big, text, cx, cy, rot, fill, size=62, scale=1.0, fg=(255, 255, 255)):
    if scale <= 0.02: return
    f = font(size * scale); tmp = Image.new("RGBA", (1000, 260), (0, 0, 0, 0)); dd = ImageDraw.Draw(tmp)
    tw = dd.textlength(text, font=f); bw, bh = tw + 80, size * scale + 56
    dd.rounded_rectangle([500 - bw / 2, 130 - bh / 2, 500 + bw / 2, 130 + bh / 2], radius=24, fill=fill, outline=(0, 0, 0), width=8)
    dd.text((500, 130), text, font=f, fill=fg, anchor="mm")
    tmp = tmp.rotate(rot, resample=Image.BICUBIC)
    big.paste(tmp, (int(cx - 500), int(cy - 130)), tmp)

def burst(d, t, t0, cx, cy, cols, n=36, life=0.8, spd=(250, 800), size=(10, 22), seed=1, grav=700):
    k = t - t0
    if k < 0 or k > life: return
    r = random.Random(seed)
    for _ in range(n):
        ang, v, sz, c = r.uniform(0, 6.28), r.uniform(*spd), r.randrange(*size), r.choice(cols)
        x = cx + math.cos(ang) * v * k; y = cy + math.sin(ang) * v * k + grav * k * k * 0.5
        z = max(2, int(sz * (1 - k / life))); d.rectangle([x, y, x + z, y + z], fill=c)

def sparkles(d, t, cx, cy, rad, n, seed, cols):
    r = random.Random(seed)
    for i in range(n):
        ang, rr, ph, sp = r.uniform(0, 6.28), r.uniform(.5, 1) * rad, r.uniform(0, 6.28), r.uniform(2, 5)
        if (math.sin(t * sp + ph) + 1) / 2 < 0.4: continue
        z = int(10 + 22 * ((math.sin(t * sp + ph) + 1) / 2)); c = cols[i % len(cols)]
        x = cx + math.cos(ang + t * 0.4) * rr; y = cy + math.sin(ang + t * 0.4) * rr * 0.8
        d.rectangle([x - z, y - 4, x + z, y + 4], fill=c); d.rectangle([x - 4, y - z, x + 4, y + z], fill=c)

# ------------------------------------------------------------------- fundo
rnd = random.Random(21)
FLOAT = [(rnd.randrange(8, W - 24), rnd.random() * 700, rnd.uniform(8, 20), rnd.randrange(0, 5), rnd.choice((16, 20, 28)))
         for _ in range(16)]
FTEX = [SP["cu"][0], SP["cu"][1], SP["cu"][3], SP["dandelion"], SP["heart"]]

def scene_idx(t):
    for i in range(len(starts) - 1, -1, -1):
        if t >= starts[i]: return i
    return 0

def draw_bg(big_low, t, i):
    d = ImageDraw.Draw(big_low)
    ac = ACCENT[i]
    for y in range(0, H, 4):
        k = y / H
        d.rectangle([0, y, W, y + 4], fill=(int(14 + 34 * k), int(18 + 8 * k), int(44 + 40 * k)))
    # grade de pixels
    for x in range(0, W, 24): d.line([x, 0, x, H], fill=(28, 34, 70))
    for y in range(int((t * 20) % 24), H, 24): d.line([0, y, W, y], fill=(28, 34, 70))
    # blocos reais flutuando
    for x, y0, sp, ti, sz in FLOAT:
        y = H + 40 - ((y0 + t * sp * 3) % (H + 80))
        im = FTEX[ti].resize((sz, sz), Image.NEAREST); im.putalpha(im.getchannel("A").point(lambda v: int(v * 0.30)))
        big_low.paste(im, (int(x), int(y)), im)
    d.rectangle([0, 0, W, 3], fill=ac)

# ------------------------------------------------------------------- UI
def draw_ui(big, t, i):
    ac = ACCENT[i]; lt = t - starts[i]
    ov = Image.new("RGBA", big.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    # barras estilo "stories"
    n = len(starts); bw = (FW - 120) / n
    for k in range(n):
        x0 = 60 + k * bw
        od.rounded_rectangle([x0, 64, x0 + bw - 10, 78], radius=7, fill=(255, 255, 255, 60))
        pr = clamp((t - starts[k]) / (ends[k] - starts[k]))
        if pr > 0: od.rounded_rectangle([x0, 64, x0 + (bw - 10) * pr, 78], radius=7, fill=ac + (255,))
    # número + título deslizando
    if i not in (0, len(starts) - 1):
        k = ease(lt / 0.35); dx = (1 - k) * -500
        od.rounded_rectangle([60 + dx, 120, 230 + dx, 250], radius=26, fill=ac + (255,), outline=(0, 0, 0, 255), width=8)
        od.text((145 + dx, 185), f"{i:02d}", font=font(84), fill=(10, 10, 20, 255), anchor="mm")
        od.rounded_rectangle([250 + dx, 140, FW - 60 + dx, 230], radius=22, fill=(8, 10, 24, 220), outline=ac + (255,), width=6)
        od.text((270 + dx + (FW - 330) / 2, 185), TITLES[i], font=font(56), fill=(255, 255, 255, 255), anchor="mm")
    # faixa de transição ao entrar em cada cena
    if 0 < i and lt < 0.4:
        x = lt / 0.4 * (FW + 500) - 500
        od.rectangle([x, 0, x + 500, FH], fill=ac + (150,))
    # legenda: painel com palavras que vão surgindo
    words = WT[i]; maxw = 880
    for size in (72, 66, 60, 56, 52, 48):               # menor fonte até caber em no máximo 3 linhas
        f = font(size); lines, cur, curw = [], [], 0; sp = od.textlength(" ", font=f)
        for idx, (w, a, b_) in enumerate(words):
            ww = od.textlength(w, font=f)
            if cur and curw + sp + ww > maxw: lines.append((cur, curw)); cur, curw = [], 0
            cur.append((idx, ww)); curw += ww + (sp if len(cur) > 1 else 0)
        lines.append((cur, curw))
        if len(lines) <= 3: break
    if t >= words[0][1] - 0.02:
        lh = int(size * 1.3); ph = len(lines) * lh + 52; cy = 1385
        od.rounded_rectangle([FW / 2 - 480, cy - ph / 2, FW / 2 + 480, cy + ph / 2], radius=34, fill=(6, 8, 20, 225),
                             outline=ac + (255,), width=6)
        y = cy - ph / 2 + 26 + lh / 2
        for ln, lw in lines:
            x = FW / 2 - lw / 2
            for idx, ww in ln:
                w, a, b_ = words[idx]
                if t >= a - 0.02:
                    od.text((x, y), w, font=f, fill=(ac if t < b_ else (255, 255, 255)) + (255,), anchor="lm")
                x += ww + sp
            y += lh
    if SOURCES[i] and lt > 0.6:
        od.text((FW / 2, 1640), SOURCES[i], font=font(32), fill=(190, 205, 235, int(255 * ease((lt - 0.6) / 0.3))), anchor="mm")
    big.alpha_composite(ov)

# ------------------------------------------------------------------- cenas
CX, CY = FW // 2, 790

def slam(lt, delay=0.0, dur=0.6):
    k = clamp((lt - delay) / dur)
    return (1 - bounce(k)) * -800, clamp(k * 4)        # deslocamento y, opacidade

def scene(big, t, i):
    lt = t - starts[i]; d = ImageDraw.Draw(big); ac = ACCENT[i]
    out = 1 - ease((t - (ends[i] - 0.15)) / 0.15) if i < len(starts) - 1 else 1.0
    bob = math.sin(t * 3.0) * 14
    dy, al = slam(lt); al *= out
    if i == 0:
        for n, (name, x, rot) in enumerate((("egg_creaking", 270, -12), ("egg_golem", 540, 0), ("egg_ghast", 810, 12))):
            dyy, aa = slam(lt, 0.12 + 0.18 * n)
            place(big, SP[name], x, 800 + dyy + (bob if n % 2 else -bob) * .6, 330, rot=rot + math.sin(t * 2 + n) * 4, alpha=aa * out,
                  glow=ac, gi=.55)
        k = back((lt - 0.2) / 0.35)
        tstroke(d, (CX, 500), "4 FATOS", font(max(10, 170 * k)), ac, stroke=14)
        sparkles(d, t, CX, 800, 460, 14, 2, (ac, (255, 255, 255)))
        sticker(big, "COM FONTES", 830, 1030, -6, (30, 30, 50), size=52, scale=back((lt - 0.8) / 0.3), fg=ac)
    elif i == 1:
        stop, res = kw(1, "PARAREM"), kw(1, "USADA")
        place(big, SP["dandelion"], CX, 640 + dy + bob, 430, rot=math.sin(t * 2.2) * 7, alpha=al, glow=(255, 214, 64), gi=.9)
        g = 0.5 + 0.3 * clamp((min(t, stop) - starts[1]) / (stop - starts[1]))
        if t >= res: g = 0.8 + 0.3 * clamp((t - res) / 2.0)
        place(big, SP["baby"], CX, 1020, 300 * g, alpha=al, glow=(255, 160, 190), gi=.35)
        # partículas verdes: descem ao parar de crescer, sobem ao voltar a crescer
        if t >= stop and out > 0:
            up = t >= res; r = random.Random(7)
            for n in range(16):
                ph = (t * 0.9 + n / 16) % 1; x = CX + r.uniform(-230, 230)
                y = (1180 - ph * 600) if up else (580 + ph * 600)
                d.rectangle([x, y, x + 16, y + 16], fill=(90, 235, 120))
        if lt > 0.9 and out > 0:
            txt = "PARA DE CRESCER" if stop <= t < res else ("VOLTA A CRESCER" if t >= res else "FILHOTE")
            col = (200, 40, 60) if stop <= t < res else ((30, 140, 70) if t >= res else (30, 30, 50))
            sticker(big, txt, CX, 335 + 0, -3, col, size=56, scale=back((lt - 0.9) / 0.3) if t < stop else 1)
    elif i == 2:
        ts = [kw(2, "PRETZEL"), kw(2, "CADEIRA"), kw(2, "DEDOS")]
        shake = 0
        for tt in ts:
            if 0 <= t - tt < 0.4: shake = max(shake, 22 * (1 - (t - tt) / 0.4))
        r = random.Random(int(t * 40))
        place(big, SP["egg_creaking"], CX + r.uniform(-shake, shake), 700 + dy + bob * .5 + r.uniform(-shake, shake), 520,
              rot=r.uniform(-shake, shake) * .4, alpha=al, glow=ac, gi=.8)
        place(big, SP["heart"], CX + 330 * math.cos(t * 1.6), 1010 + 60 * math.sin(t * 1.6), 150, alpha=al * 0.9, glow=ac, gi=.5)
        for tt, (txt, x, y, rot, col) in zip(ts, (("PRETZEL", 300, 440, -8, (150, 90, 40)),
                                                  ("CADEIRA", 780, 520, 7, (90, 60, 40)),
                                                  ("DEDOS", 330, 1000, -5, (200, 120, 60)))):
            if t >= tt and out > 0:
                sticker(big, txt + "!", x, y, rot, col, size=62, scale=back((t - tt) / 0.3))
                burst(d, t, tt, x, y, [ac, (255, 255, 255)], seed=int(tt * 10))
    elif i == 3:
        lost, got = kw(3, "PERDEU"), kw(3, "ENTROU")
        mv = ease((t - got) / 0.7)
        gx, gs = 330 + (CX - 330) * mv, 400 + 120 * mv
        place(big, SP["egg_golem"], gx, 760 + dy + bob * .5, gs, alpha=al, glow=ac, gi=.7 + .5 * mv)
        place(big, SP["egg_allay"], 750, 760 + dy - bob * .5, 400, alpha=al * (1 - mv), glow=(110, 190, 255), gi=.5)
        if mv < 1:
            tstroke(d, (CX, 800), "VS", font(110), (255, 255, 255), stroke=12)
        if t >= lost and out > 0:
            k = back((t - lost) / 0.3)
            if t < got: sticker(big, "2021: PERDEU", 330, 470, -6, (190, 35, 55), size=54, scale=k)
            if t < got: sticker(big, "ALLAY VENCEU", 760, 1070, 5, (50, 110, 200), size=50, scale=k)
        if t >= got and out > 0:
            sticker(big, "2025: ADICIONADO!", CX, 440, -3, (30, 140, 70), size=60, scale=back((t - got) / 0.35))
            sparkles(d, t, CX, 760, 380, 14, 9, (ac, (255, 255, 255)))
            burst(d, t, got, CX, 760, [ac, (255, 255, 255)], seed=5)
    elif i == 4:
        place(big, SP["ghast"], CX, 720 + dy + bob, 520, rot=math.sin(t * 1.8) * 5, alpha=al, glow=ac, gi=.7)
        for n in range(3):
            a = t * 1.3 + n * 2.09
            tstroke(d, (CX + 360 * math.cos(a), 700 + 150 * math.sin(a)), "?", font(120 + 20 * math.sin(a * 2)), ac, stroke=10)
        marks = [(kw(4, "RESTOS"), "RESTOS?", 300, 470, -7), (kw(4, "OVO"), "OVO?", 790, 520, 6),
                 (kw(4, "OUTRA"), "OUTRA COISA?", 400, 1030, -3)]
        for tt, txt, x, y, rot in marks:
            if t >= tt and out > 0:
                sticker(big, txt, x, y, rot, (60, 30, 100), size=58, scale=back((t - tt) / 0.3))
    elif i == 5:
        place(big, SP["dandelion"], CX, 760 + dy + bob, 480, rot=math.sin(t * 2.2) * 7, alpha=al, glow=(255, 214, 64), gi=.9)
        sparkles(d, t, CX, 760, 420, 16, 4, (ac, (255, 255, 255), (255, 214, 64)))
        k = ease((lt - 0.25) / 0.3); sc = 1 + 0.05 * math.sin(t * 8)
        d.rounded_rectangle([CX - 400 * k, 1080 - 85 * k, CX + 400 * k, 1080 + 85 * k], radius=30, fill=(255, 40, 70),
                            outline=(0, 0, 0), width=10)
        if k > .8: d.text((CX, 1080), "SEGUIR  +  CURTIR", font=font(70 * sc), fill=(255, 255, 255), anchor="mm")

def render(fi):
    t = fi / FPS; i = scene_idx(t)
    low = Image.new("RGB", (W, H)); draw_bg(low, t, i)
    big = low.resize((FW, FH), Image.NEAREST).convert("RGBA")
    scene(big, t, i); draw_ui(big, t, i)
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

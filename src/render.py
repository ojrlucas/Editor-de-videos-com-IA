"""Renderiza o vídeo 1080x1920@30 frame a frame (PIL+numpy) e codifica com FFmpeg (H.264)."""
import json, math, subprocess, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, "src")
from script_data import SEGMENTS, FPS, DURATION
from shots import SHOTS, IMG

W, H = 1080, 1920
PY0, PH = 420, 1080                       # painel (y, altura)
FB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FBLK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
def font(sz, black=False): return ImageFont.truetype(FBLK if black else FB, sz)
PINK, ORANGE, PURPLE, BLUE, YEL = (255, 45, 140), (255, 140, 40), (150, 60, 255), (40, 190, 255), (255, 225, 70)
ease_out = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3
def back(x, s=1.70158):
    x = min(max(x, 0), 1); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2

# ---------- imagens ----------
src, bgs = {}, {}
for n, *_ in SHOTS:
    im = Image.open(IMG.format(n)).convert("RGB"); src[n] = im
    bg = im.resize((int(H * 16 / 9 * 0.62), int(H * 0.62)))      # cobre 1080x1920 apos recorte
    sc = max(int(W * 1.3) / im.width, int(H * 1.3) / im.height)
    b = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR).resize((int(im.width * sc / 6), int(im.height * sc / 6)))
    b = b.filter(ImageFilter.GaussianBlur(6)).resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
    bgs[n] = np.asarray(b).astype(np.float32) * 0.42

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 * 0.7 + ((yy - H / 2) / (H / 2)) ** 2 * 0.6)
vig = np.clip(vig, 0.25, 1)[..., None]
grad = np.zeros((H, W, 3), np.float32)               # grade rosa/roxo -> laranja/azul
t_ = (yy / H)[..., None]
grad[:] = np.array(PURPLE) * (1 - t_) + np.array(ORANGE) * t_
scan = (1 - 0.06 * ((yy % 4) < 1))[..., None]
rng = np.random.default_rng(1)
_ty = (yy[:, :1] / H)[..., None]
READ = (1 - 0.72 * np.clip(1 - _ty / 0.26, 0, 1) ** 1.6 - 0.80 * np.clip((_ty - 0.66) / 0.34, 0, 1) ** 1.3)

# ---------- legendas: tempo por palavra ----------
timing = json.load(open("build/work/timing.json"))
words = []   # (palavra, t0, t1, destaque)
chunks = []  # (t0, t1, [indices])
dummy = ImageDraw.Draw(Image.new("RGB", (4, 4)))
def wrap(ws, fnt=None, maxw=930):
    fnt = fnt or font(84, True); lines, cur = [], []
    for w in ws:
        trial = " ".join(x[0] for x in cur + [w])
        if cur and dummy.textlength(trial, fnt) > maxw: lines.append(cur); cur = [w]
        else: cur.append(w)
    return lines + [cur]
for sid, a, b, text, keys in SEGMENTS:
    tm = timing[sid]; ws = text.split()
    wt = [len(w.strip(",.?!:")) + 2 + (4 if w[-1] in ",.?!:" else 0) for w in ws]
    tot = sum(wt); t = tm["start"]; seg = []
    for w, k in zip(ws, wt):
        d = tm["dur"] * k / tot
        key = w.lower() in keys or w.lower().strip(",.?!:") in keys
        words.append((w.upper(), t, t + d, key)); seg.append(len(words) - 1); t += d
    # agrupa em blocos de ate 4 palavras / 2 linhas
    i = 0
    while i < len(seg):
        j = min(i + 4, len(seg))
        while j - i > 1 and len(wrap([words[k] for k in seg[i:j]])) > 2: j -= 1
        chunks.append((words[seg[i]][1], tm["start"] + tm["dur"] + 0.15 if j == len(seg) else words[seg[j]][1], seg[i:j])); i = j
with open("assets/subs/legendas.srt", "w") as f:
    ts = lambda s: f"{int(s//3600):02}:{int(s%3600//60):02}:{int(s%60):02},{int(s%1*1000):03}"
    for n, (a, b, idx) in enumerate(chunks, 1):
        f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{' '.join(words[k][0] for k in idx)}\n\n")

def text_layer(size, items):
    """items: lista de (texto, x, y, fonte, cor, anchor, stroke) -> RGBA"""
    im = Image.new("RGBA", size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for tx, x, y, f, col, anc, sw in items:
        d.text((x + 4, y + 6), tx, font=f, fill=(0, 0, 0, 170), anchor=anc, stroke_width=sw)
        d.text((x, y), tx, font=f, fill=col, anchor=anc, stroke_width=sw, stroke_fill=(10, 4, 20, 255))
    return im
def paste(canvas, layer, x=0, y=0, alpha=1.0):
    a = np.asarray(layer).astype(np.float32); al = a[..., 3:4] / 255 * alpha
    h, w = a.shape[:2]
    y0, x0 = max(y, 0), max(x, 0); y1, x1 = min(y + h, H), min(x + w, W)
    if y1 <= y0 or x1 <= x0: return
    sub = a[y0 - y: y1 - y, x0 - x: x1 - x]; sal = al[y0 - y: y1 - y, x0 - x: x1 - x]
    canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - sal) + sub[..., :3] * sal

def scale_layer(layer, s):
    if abs(s - 1) < 0.01: return layer, 0, 0
    w, h = layer.size; nw, nh = max(1, int(w * s)), max(1, int(h * s))
    return layer.resize((nw, nh), Image.BILINEAR), (w - nw) // 2, (h - nh) // 2

# ---------- headline por cena ----------
def headline(t):
    """retorna (linhas[(texto, cor)], inicio) da cena atual"""
    if t < 3.0: return [("A ROCKSTAR", (255, 255, 255)), ("SURPREENDEU OS FÃS", PINK)], 0.0
    if t < 8.1: return [("GALERIA DE LANÇAMENTO", (255, 255, 255)), ("2 SEMANAS PARA GTA VI", ORANGE)], 3.0
    if t < 16.1: return [("O QUE FOI MOSTRADO", (255, 255, 255)), ("VICE CITY • JASON • LUCIA", BLUE)], 8.1
    if t < 21.1: return [("O DETALHE QUE", (255, 255, 255)), ("CHAMOU ATENÇÃO", PINK)], 16.1
    return [("QUAL TE CONVENCEU?", (255, 255, 255)), ("COMENTA AÍ 👇".replace(" 👇", ""), YEL)], 21.1

def map_src(n, t, sx, sy, shot, ex):
    """coordenada (sx,sy) em [0..1] da imagem -> pixel do frame 9:16, segundo a camera do plano"""
    z0, z1, p0, p1 = shot[3]; k = min(max((t - shot[1]) / (shot[2] - shot[1]), 0), 1); k = k * k * (3 - 2 * k)
    z = (z0 + (z1 - z0) * k) * ex; ch = 1080 / z; cw = ch * 9 / 16; p = p0 + (p1 - p0) * k
    cx = p * (1920 - cw) + cw / 2
    return (sx * 1920 - (cx - cw / 2)) * (W / cw), (sy * 1080 - (540 - ch / 2)) * (H / ch)

def render_frame(f):
    t = f / FPS
    shot = next(s for s in SHOTS if s[1] <= t < s[2] + 1e-9 or s is SHOTS[-1] and t >= s[1])
    n = shot[0]; tl = t - shot[1]; dur = shot[2] - shot[1]
    k = min(max(tl / dur, 0), 1); ke = k * k * (3 - 2 * k)
    # punch de entrada (corte)
    pk = ease_out(tl / 0.28) if shot is not SHOTS[0] else 1.0
    punch = 1 + 0.16 * (1 - pk) ** 2
    z0, z1, p0, p1 = shot[3]
    z = (z0 + (z1 - z0) * ke) * punch; p = p0 + (p1 - p0) * ke
    ch = 1080 / z; cw = ch * 9 / 16; cx = p * (1920 - cw) + cw / 2
    im = src[n]
    box = (cx - cw / 2, 540 - ch / 2, cx + cw / 2, 540 + ch / 2)
    panel = np.asarray(im.resize((W, H), Image.LANCZOS, box=box).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))).astype(np.float32)
    ca = int(16 * (1 - pk)); off = int(140 * (1 - pk) ** 2)
    if ca:
        panel[:, :, 0] = np.roll(panel[:, :, 0], ca, axis=1); panel[:, :, 2] = np.roll(panel[:, :, 2], -ca, axis=1)
    gp = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    panel = np.clip(panel * 1.05 + np.array(PINK) * (1 - gp) * 0.10 + np.array(BLUE) * gp * 0.10 - 8, 0, 255)
    if off: panel = np.roll(panel, off, axis=1)
    canvas = panel * READ
    canvas *= vig * scan
    # ----- elementos graficos sobre o painel -----
    if shot[0] == 7:                                    # anel de destaque na cabeça do Jason
        a = ease_out((t - 16.7) / 0.5)
        if a > 0:
            px, py = map_src(n, t, 0.60, 0.235, shot, 1)
            ring = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ring)
            r = 150 * a * (1 + 0.04 * math.sin(t * 9))
            ccx, ccy = px, py
            d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], outline=YEL + (255,), width=8)
            for ang in range(0, 360, 90):
                u = math.radians(ang + t * 90)
                d.line([ccx + math.cos(u) * (r + 8), ccy + math.sin(u) * (r + 8), ccx + math.cos(u) * (r + 36), ccy + math.sin(u) * (r + 36)], fill=YEL + (255,), width=8)
            paste(canvas, ring, 0, 0)
            lab = text_layer((760, 170), [("SEM CAPACETE", 380, 55, font(64, True), YEL + (255,), "mm", 6), ("segundo a Top Gear", 380, 125, font(34), (255, 255, 255, 255), "mm", 4)])
            s = back((t - 17.1) / 0.45)
            if s > 0:
                l2, ox, oy = scale_layer(lab, max(s, 0.01))
                paste(canvas, l2, 160 + ox, 1250 + oy, min(1, (t - 17.1) / 0.2))
    # headline animada (por cena)
    lines, t0 = headline(t); lt = t - t0
    hl = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
    for i, (tx, col) in enumerate(lines):
        sz = 74 if len(tx) < 20 else 60
        l = text_layer((W, 130), [(tx, W // 2, 65, font(sz, True), col + (255,), "mm", 5)])
        s = back((lt - i * 0.12) / 0.4); al = min(1, max(0, (lt - i * 0.12) / 0.18))
        if s > 0.02:
            l2, ox, oy = scale_layer(l, s); paste_lay = Image.new("RGBA", (W, 260), (0, 0, 0, 0)); paste_lay.paste(l2, (ox, 20 + i * 100 + oy), l2)
            hl = Image.alpha_composite(hl, Image.eval(paste_lay, lambda v: v)) if al >= 1 else Image.alpha_composite(hl, paste_lay)
    paste(canvas, hl, 0, 150)
    # contador "37" (cena de contexto)
    if 3.0 <= t < 8.1:
        ct = t - 3.0
        val = 37 if ct > 1.0 else int(37 * ease_out(ct / 1.0))
        s = back((ct - 0.1) / 0.5)
        if s > 0:
            big = text_layer((760, 330), [(str(val), 190, 150, font(250, True), YEL + (255,), "mm", 8),
                                          ("NOVAS", 490, 85, font(60, True), (255, 255, 255, 255), "mm", 5),
                                          ("IMAGENS", 490, 160, font(60, True), (255, 255, 255, 255), "mm", 5),
                                          ("INÉDITAS", 490, 235, font(60, True), PINK + (255,), "mm", 5)])
            b2, ox, oy = scale_layer(big, s); paste(canvas, b2, 40 + ox, 470 + oy, min(1, ct / 0.15))
    if 6.5 <= t < 8.1:
        al = ease_out((t - 6.5) / 0.3)
        c = text_layer((820, 110), [("LANÇAMENTO: 19 NOV 2026", 410, 55, font(54, True), (255, 255, 255, 255), "mm", 5)])
        bg = Image.new("RGBA", (860, 120), (0, 0, 0, 0)); ImageDraw.Draw(bg).rounded_rectangle([0, 0, 859, 119], 18, fill=(10, 4, 25, 200), outline=ORANGE + (255,), width=4)
        bg.paste(c, (20, 5), c); paste(canvas, bg, 110, 1290, al)
    if t >= 23.1:
        al = ease_out((t - 23.2) / 0.35)
        bg = Image.new("RGBA", (900, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(bg)
        d.rounded_rectangle([0, 0, 899, 99], 18, fill=(10, 4, 25, 205), outline=PINK + (255,), width=4)
        d.text((450, 50), "PS5 • XBOX SERIES X|S • 19 NOV", font=font(44, True), fill=(255, 255, 255, 255), anchor="mm")
        paste(canvas, bg, 90, 1300, al)
    if 19.1 <= t < 21.1:
        al = ease_out((t - 19.2) / 0.3)
        bg = Image.new("RGBA", (900, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(bg)
        d.rounded_rectangle([0, 0, 899, 99], 18, fill=(10, 4, 25, 205), outline=BLUE + (255,), width=4)
        d.text((450, 50), "ROSTOS COM DETALHE ABSURDO", font=font(44, True), fill=(255, 255, 255, 255), anchor="mm")
        paste(canvas, bg, 90, 1300, al)
    # legendas (max 2 linhas)
    cur = next((c for c in chunks if c[0] <= t < c[1]), None)
    if cur:
        a, b, idx = cur; ct = t - a
        ws = [words[i] for i in idx]
        sf = font(84, True); full = " ".join(w[0] for w in ws)
        lns = wrap(ws, sf)
        lay = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for li, lw in enumerate(lns):
            tw = dummy.textlength(" ".join(x[0] for x in lw), sf); x = (W - tw) / 2; y = 70 + li * 110
            for w in lw:
                active = w[1] <= t < w[2]
                col = (PINK if w[3] else (255, 255, 255)) if not active else (YEL if not w[3] else (255, 120, 190))
                if w[3] and not active: col = ORANGE
                d.text((x + 4, y + 6), w[0], font=sf, fill=(0, 0, 0, 200), anchor="lm", stroke_width=10)
                d.text((x, y), w[0], font=sf, fill=col + (255,), anchor="lm", stroke_width=10, stroke_fill=(8, 3, 18, 255))
                x += dummy.textlength(w[0] + " ", sf)
        s = back(ct / 0.18, 2.2); s = max(s, 0.5)
        l2, ox, oy = scale_layer(lay, s); paste(canvas, l2, ox, 1470 + oy, min(1, ct / 0.08))
    # credito + progresso
    cred = text_layer((W, 60), [("Imagens: Rockstar Games (galeria oficial) • via Push Square", W // 2, 30, font(26), (225, 220, 240, 255), "mm", 3)])
    paste(canvas, cred, 0, 1835, 0.9)
    canvas[1905:1915, :int(W * t / DURATION)] = np.array(PINK) * (1 - xx[1905:1915, :int(W * t / DURATION), None] / W) + np.array(ORANGE) * (xx[1905:1915, :int(W * t / DURATION), None] / W)
    # flash no corte + grao
    if shot is not SHOTS[0] and tl < 0.2:
        fa = 0.55 * (1 - tl / 0.2) ** 2; canvas = canvas * (1 - fa) + np.array([255, 190, 235]) * fa
    if f < 6: canvas *= f / 6
    canvas += rng.normal(0, 4, (H, W, 1)).astype(np.float32)
    return np.clip(canvas, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    nf = int(DURATION * FPS)
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        for ts in (0.9, 2.2, 4.0, 7.2, 10.5, 17.8, 20.0, 24.0):
            Image.fromarray(render_frame(int(ts * FPS))).save(f"build/work/f_{ts}.jpg", quality=88)
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", "assets/audio/mix_final.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "17",
                           "-pix_fmt", "yuv420p", "-r", str(FPS), "-af", "loudnorm=I=-16:TP=-1.5:LRA=7,apad", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                           "-frames:v", str(nf), "-t", str(DURATION), "-movflags", "+faststart", "output/gta6_novidade.mp4"], stdin=subprocess.PIPE)
    for f in range(nf):
        ff.stdin.write(render_frame(f).tobytes())
        if f % 75 == 0: print("frame", f, flush=True)
    ff.stdin.close(); ff.wait(); print("done", ff.returncode)

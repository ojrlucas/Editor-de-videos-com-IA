"""Gera legendas .srt e .vtt a partir de src/generated/captions.json (mesmas páginas exibidas no vídeo)."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
caps = json.load(open(f"{ROOT}/src/generated/captions.json"))
pages = []
for p in caps:
    cur, chars = [], 0
    for w in p["words"]:
        if cur and (chars + len(w["w"]) > 26 or len(cur) >= 5):
            pages.append(cur); cur, chars = [], 0
        cur.append(w); chars += len(w["w"]) + 1
    if cur: pages.append(cur)
def ts(x, sep):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f"{h:02d}:{m:02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)):03d}"
os.makedirs(f"{ROOT}/output", exist_ok=True)
srt, vtt = [], ["WEBVTT\n"]
for i, pg in enumerate(pages, 1):
    a, b = pg[0]["s"], pg[-1]["e"] + 0.2
    text = " ".join(w["w"] for w in pg).upper()
    srt.append(f"{i}\n{ts(a, ',')} --> {ts(b, ',')}\n{text}\n")
    vtt.append(f"{ts(a, '.')} --> {ts(b, '.')}\n{text}\n")
open(f"{ROOT}/output/legendas.srt", "w", encoding="utf-8").write("\n".join(srt))
open(f"{ROOT}/output/legendas.vtt", "w", encoding="utf-8").write("\n".join(vtt))
print("legendas:", len(pages), "blocos")

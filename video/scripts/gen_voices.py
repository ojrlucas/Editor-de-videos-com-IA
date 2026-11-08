"""Gera as falas (narrador e voz feminina sintética da ligação) com Kokoro TTS (Apache-2.0).
Uso: python gen_voices.py <kokoro.onnx> <voices.bin> <out_dir>
Vozes sintéticas originais do modelo — não imitam pessoas reais."""
import sys, soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
model, voices, out = sys.argv[1:4]
k = Kokoro(model, voices)
LINES = {
 # nome: (texto, voz, velocidade) — velocidade perto de 1.0 preserva a entonação natural
 "n1a": ("E se sua mãe te ligasse pedindo socorro?", "pm_santa", 1.1),
 "n1b": ("Mas não fosse ela!", "pm_santa", 1.0),
 "n2":  ("A inteligência artificial captura sua voz, e a reconstrói!", "pm_santa", 1.08),
 "n3":  ("Apenas alguns segundos de áudio podem ser suficientes para um golpe!", "pm_santa", 1.1),
 "call":("Filho... preciso da sua ajuda...", "pf_dora", 0.78),
 "n5":  ("A voz era artificial!", "pm_santa", 0.95),
 "n6a": ("Sua voz pode ser clonada!", "pm_santa", 1.0),
 "n6b": ("Você saberia identificar uma ligação falsa?", "pm_santa", 1.2),
}
for name,(t,v,s) in LINES.items():
    a, sr = k.create(t, voice=v, speed=s, lang="pt-br")
    idx = np.where(np.abs(a) > 0.01)[0]          # corta silêncio das pontas
    a = a[max(idx[0]-int(0.03*sr),0): idx[-1]+int(0.08*sr)]
    sf.write(f"{out}/{name}.wav", a, sr)
    print(name, round(len(a)/sr,2), "s", sr)

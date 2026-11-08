#!/usr/bin/env python3
"""Converte a narração (Kokoro) para o timbre da voz de referência do usuário (kNN-VC, MIT).
Uso: python clone_voice.py <referencia.wav> <narracao_in.wav> <narracao_out.wav> [k]"""
import sys, os, torch, torchaudio, soundfile as sf, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knnvc'))
from hubconf import knn_vc

ref, inp, out = sys.argv[1:4]
k = int(sys.argv[4]) if len(sys.argv) > 4 else 4
torch.set_num_threads(4)
m = knn_vc(pretrained=True, prematched=True, device='cpu')
r, rsr = sf.read(ref, dtype='float32'); r = r if r.ndim == 1 else r[:, 0]
r = torchaudio.functional.resample(torch.from_numpy(r), rsr, 16000)
ms = m.get_matching_set([r])
print('matching set', tuple(ms.shape))
a, sr = sf.read(inp, dtype='float32'); a = a if a.ndim == 1 else a[:, 0]
w = torchaudio.functional.resample(torch.from_numpy(a)[None], sr, 16000)
q = m.get_features(w)  # aceita tensor
y = m.match(q, ms, topk=k)
y = torchaudio.functional.resample(y[None] if y.ndim == 1 else y, 16000, 48000).numpy().squeeze()
y = np.pad(y, (0, max(0, len(a) - len(y))))[:len(a)]
sf.write(out, y, 48000)
print('ok', len(y) / 48000)

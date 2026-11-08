"""Voz clonada (XTTS-v2) a partir de uma amostra da SUA voz.

Uso nos geradores:  VOZ=xtts python3 gerar_fatos.py saida.mp4
Variáveis: XTTS_DIR (modelo, padrão /tmp/xtts), XTTS_REF (amostra .wav, padrão voz_amostra/amostra_24k.wav),
XTTS_SPEED (padrão 1.08), XTTS_TEMP (padrão 0.65).

Licença do modelo: Coqui Public Model License (uso NÃO comercial).
"""
import os
import numpy as np

_AQUI = os.path.dirname(os.path.abspath(__file__))
_modelo = None
_latentes = None

def _carregar():
    global _modelo, _latentes
    if _modelo is not None:
        return
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    d = os.environ.get("XTTS_DIR", "/tmp/xtts")
    ref = os.environ.get("XTTS_REF", os.path.join(_AQUI, "voz_amostra", "amostra_24k.wav"))
    cfg = XttsConfig(); cfg.load_json(os.path.join(d, "config.json"))
    m = Xtts.init_from_config(cfg)
    m.load_checkpoint(cfg, checkpoint_dir=d, eval=True, use_deepspeed=False)
    _latentes = m.get_conditioning_latents(audio_path=[ref])
    _modelo = m

def sintetizar(textos):
    """lista de textos -> lista de (np.float32, 24000)."""
    _carregar()
    gpt, spk = _latentes
    vel = float(os.environ.get("XTTS_SPEED", "1.08")); temp = float(os.environ.get("XTTS_TEMP", "0.65"))
    out = []
    for t in textos:
        r = _modelo.inference(t, "pt", gpt, spk, temperature=temp, speed=vel, enable_text_splitting=True)
        out.append((np.asarray(r["wav"], np.float32), 24000))
    return out

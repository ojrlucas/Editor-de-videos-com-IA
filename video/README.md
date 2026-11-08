# O PLANETA ONDE CHOVE VIDRO! — HD 189733 b

Vídeo vertical de **25 s** (1080×1920, 30 fps, H.264 + AAC), feito com **Remotion** + shaders WebGL procedurais
(planeta 3D, nuvens volumétricas em paralaxe, partículas/cristais com profundidade de campo).
**Sem música**: somente narração, efeitos pontuais e vento/ruído atmosférico.

Resultado: `../output/planeta_chuva_vidro.mp4`

## Estrutura
- `src/` – composição (Remotion): `Video.tsx` (montagem), `shaders.ts` (planeta e nuvens GLSL), `Particles.tsx`,
  `Headline.tsx`, `Captions.tsx`, `Hud.tsx`, `anim.ts` (câmeras/curvas), `timeline.ts`
- `scripts/build_audio.py` – narração + SFX + mixagem + `public/timeline.json` (legendas sincronizadas)
- `scripts/clone_voice.py` + `scripts/knnvc/` – converte o timbre da narração para a voz de referência (kNN-VC, MIT)
- `public/audio/` – `narracao.wav`, `sfx.wav`, `audio_final.wav`, `referencia_voz_usuario.wav`
- `public/fonts/` – Montserrat e Rajdhani (SIL OFL, via @fontsource)

## Renderizar
```bash
cd video && npm install
# (opcional) refazer o áudio — requer Python 3 com requirements.txt + torch/torchaudio
#   modelos: kokoro-v1.0.onnx e voices-v1.0.bin (thewh1teagle/kokoro-onnx, release model-files-v1.0)
#            WavLM-Large.pt e prematch_g_02500000.pt (bshall/knn-vc, release v0.1) em ~/.cache/torch/hub/checkpoints
python3 scripts/build_audio.py --model kokoro-v1.0.onnx --voices voices-v1.0.bin \
        --clone-ref public/audio/referencia_voz_usuario.wav   # omita --clone-ref para a voz neural padrão (pm_alex)
npm run render
```
O Chromium é configurado em `remotion.config.ts` (`/opt/pw-browsers/chromium`); ajuste o caminho no seu ambiente.

## Precisão científica
- **Observado:** HD 189733 b é um exoplaneta "Júpiter quente"; a cor azulada foi medida com o Hubble.
- **Hipótese:** nuvens de silicatos ("vidro") vêm de modelos atmosféricos; chuva de vidro **não** foi observada diretamente.
- Todas as imagens são visualizações artísticas procedurais, **não fotografias** (aviso permanente no rodapé).

# SUA VOZ PODE SER CLONADA — vídeo dark viral (25 s, 9:16)

Vídeo de suspense tecnológico produzido 100 % por código com **Remotion** (React + Chromium + FFmpeg).
Sem apresentador, sem imagens de banco, sem URLs externas: todo visual é vetorial/procedural
(SVG, CSS 3D e Canvas 2D) e todo áudio é gerado localmente (TTS + síntese).

| Item | Valor |
|---|---|
| Duração | 25,000 s (750 quadros) |
| Formato | 1080 × 1920 (9:16), 30 fps |
| Vídeo / Áudio | H.264 (yuv420p, CRF 17) / AAC 192 kbps estéreo 48 kHz |
| Saída | `output/sua_voz_pode_ser_clonada.mp4` |

> Este projeto vive em `video/`, separado do app Flutter "Prazo" que já existia na raiz do repositório
> (que não foi alterado).

## Estrutura

```
video/
├─ src/
│  ├─ index.ts · Root.tsx          composição "DarkViral" (1080×1920 @30, 750 quadros)
│  ├─ DarkViral.tsx                linha do tempo: cenas, transições, glitch global, legendas, grão
│  ├─ sync.json                    ⏱ tempos de falas/eventos — lido pelo Python (áudio) e pelo React (imagem)
│  ├─ theme.ts                     paleta (#050609 #087EFF #FF263D #F5F5F5), fontes, área segura
│  ├─ scenes/Scene1..6.tsx         uma cena por arquivo (gancho → captura → reconstrução → ligação → revelação → final)
│  ├─ components/                  BigText, Captions, Glitch (RGB split + fatias), Canvas2D, PhoneUI, Overlays…
│  ├─ lib/                         time (contexto de quadro global, easing, PRNG determinístico, envelope de áudio),
│  │                               silhouette (busto feminino amostrado em partículas), fonts
│  └─ generated/                   envelope.json (amplitude de áudio por quadro) e captions.json (palavras com tempo)
├─ scripts/
│  ├─ setup_tts.sh                 venv Python + modelo Kokoro (baixa ~350 MB do GitHub Releases)
│  ├─ gen_voices.py                narração e voz da ligação (Kokoro TTS, vozes sintéticas pt-BR)
│  ├─ gen_audio.py                 trilha, efeitos, ducking, mix, envelope e legendas (numpy/scipy)
│  ├─ build_audio.sh               pipeline de áudio completo + loudnorm (-14 LUFS)
│  ├─ make_srt.py                  gera legendas .srt/.vtt
│  ├─ render.sh                    renderização final do MP4
│  └─ validate.sh                  verificação automática do MP4 (duração, resolução, pretos, loudness, folha de contato)
├─ public/audio/                   master.wav (usado no vídeo) + stems em FLAC (música, efeitos, narração, ligação)
├─ public/fonts/                   Anton, Inter, JetBrains Mono (SIL OFL, via @fontsource) — carregadas localmente
├─ audio_src/                      falas cruas geradas pelo TTS (WAV)
└─ output/                         MP4 final, legendas .srt/.vtt, folha de contato
```

## Reproduzir

Requisitos: Node 18+, FFmpeg, Python 3.10+, Chromium/Chrome (o `remotion.config.ts` usa
`/opt/pw-browsers/chromium-1243/chrome-linux64/chrome` se existir, ou a variável `REMOTION_BROWSER`;
caso contrário o Remotion baixa o próprio Chrome).

```bash
cd video
npm install
bash scripts/setup_tts.sh      # só na 1ª vez (só é necessário para REGERAR o áudio)
bash scripts/build_audio.sh    # opcional: os áudios já estão em public/audio e audio_src
bash scripts/render.sh         # gera output/sua_voz_pode_ser_clonada.mp4  (~10 min em 4 núcleos)
bash scripts/validate.sh       # confere o resultado
npm run studio                 # pré-visualização interativa no navegador
```

Para regerar só a mixagem sem refazer o TTS: `SKIP_VOICES=1 bash scripts/build_audio.sh`.

## Como o áudio e a imagem se sincronizam

* `src/sync.json` é a **fonte única** dos instantes (falas, impactos, glitches, batimentos, fragmentos de voz).
  `gen_audio.py` posiciona sons nesses tempos; as cenas usam os mesmos tempos para animar.
* `envelope.json` guarda a amplitude real da fala/música/efeitos por quadro: ondas, anéis, vinhetas e
  fragmentos reagem ao áudio verdadeiro (não a uma animação fingida).
* A música cresce até 16 s (revelação), cai ao vácuo 15,88–16,0 s, há silêncio breve após "A VOZ ERA ARTIFICIAL"
  (18,95–20,0 s) e a trilha retorna sombria até o golpe grave final em 24,72 s.
* A música e os efeitos são rebaixados automaticamente (ducking) enquanto a voz fala.

## Roteiro narrado (e legendas)

| Tempo | Fala |
|---|---|
| 0,1 s | "E se sua mãe te ligasse pedindo socorro?" |
| 2,6 s | "Mas não fosse ela." |
| 4,1 s | "A inteligência artificial captura sua voz, e a reconstrói." |
| 7,75 s | "Apenas alguns segundos de áudio podem ser suficientes para um golpe." |
| 11,9 s | (voz feminina da ligação) "Filho... preciso da sua ajuda..." |
| 17,0 s | "A voz era artificial." |
| 20,1 s | "Sua voz pode ser clonada." |
| 22,2 s | "Você saberia identificar uma ligação falsa?" |

Palavras em destaque nas legendas: **CLONADA / SOCORRO / FALSA / GOLPE / ARTIFICIAL (final)** em vermelho;
**INTELIGÊNCIA ARTIFICIAL** em azul. Área segura respeitada: legendas entre y = 1328–1480 px (base livre para a UI das
plataformas) e textos principais acima de y ≈ 230 px do topo.

## Licenças e origem dos recursos

* **Voz:** [Kokoro-82M ONNX](https://github.com/thewh1teagle/kokoro-onnx) (Apache-2.0), vozes sintéticas originais
  `pm_santa` (narrador) e `pf_dora` (ligação). Não imitam pessoas reais.
* **Trilha e efeitos:** sintetizados do zero em `scripts/gen_audio.py` (sem samples de terceiros).
* **Fontes:** Anton, Inter e JetBrains Mono (SIL Open Font License 1.1).
* **Imagens:** nenhuma imagem externa — tudo desenhado em SVG/CSS/Canvas. A interface do celular é original
  (sem marcas).
* A ficção do vídeo (interface "Síntese de voz", "BPM", etc.) é ilustrativa; o vídeo **não** afirma que a clonagem
  exige um tempo exato de áudio — apresenta como possibilidade ("podem ser suficientes").

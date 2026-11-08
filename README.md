# Vídeo "dark viral": a novidade de GTA 6 (25 s, 9:16)

Saída: `output/gta6_novidade.mp4` — 1080×1920, 30 fps, H.264 (High) + AAC, **25,000 s**, pt-BR, sem música.

**Notícia:** em 05/11/2026 a Rockstar divulgou ~37 novas imagens oficiais de GTA 6 a duas semanas do lançamento (19/11). Veja `SOURCES.md`.

## Estrutura
- `src/script_data.py` roteiro e janelas de tempo · `src/shots.py` decupagem (planos, zoom/pan, cortes)
- `src/make_voice.py` narração · `src/make_audio.py` SFX + mix · `src/render.py` vídeo + legendas (`assets/subs/legendas.srt`)
- `assets/images` imagens oficiais · `assets/audio` narração e SFX · `build_video.sh` roda tudo

## Recriar
`./build_video.sh` (requer ffmpeg, Pillow, numpy, espeak-ng, mbrola, mbrola-br1).

## Limitações honestas
- **Voz:** o ambiente não permitia serviços de TTS neural (pedido de liberação negado), então a voz é MBROLA/eSpeak: masculina e inteligível, mas **mais sintética do que o "natural/aveludada" pedido**. Para trocar, gere os `.wav` por trecho com um TTS melhor (ex.: Edge TTS `pt-BR-AntonioNeural`) e substitua em `make_voice.py`.
- Não consegui ouvir o áudio; a verificação foi técnica (duração, loudness −15,9 LUFS, pico −4,5 dBFS, composição só voz+SFX).
- Tempos das legendas por palavra são proporcionais ao tamanho da palavra (sem alinhamento forçado).
- O primeiro quadro tem fade-in de ~0,2 s a partir do preto.
- Contagem de imagens varia entre veículos (37/39/"quase 40").
# Prazo — organizador de tarefas com prazo e alerta que "liga"

App Flutter (Android em foco, iOS com notificações comuns) para tarefas **com data limite**.

## Recursos
- Tarefas com título, anotações, **prazo (data + hora)**, prioridade, categoria e subtarefas com progresso
- **Lembretes** configuráveis: 1 dia, 2 h, 1 h, 30 min, 10 min antes e no horário
- **"Me ligar antes de vencer"**: por padrão 10 min antes (5/10/15/30/60 configurável). Dispara um alerta em
  **tela cheia estilo ligação**, com toque insistente e vibração, inclusive com o celular bloqueado, com
  botões **Atender / Concluir / Adiar 10 min**
- Filtros (Todas, Hoje, Próximas, Atrasadas, Concluídas), busca, categorias, agrupamento por dia
- Deslizar para concluir/excluir, com **Desfazer**
- Estatísticas (taxa de conclusão, últimos 7 dias, por prioridade)
- Alarmes reagendados após reiniciar o celular; dados salvos localmente (offline)
- Tema claro/escuro automático, interface em português

> **Sobre "ligar":** o app não faz uma chamada telefônica de verdade (isso exigiria um servidor e um
> serviço como Twilio). Ele simula a ligação com uma notificação de tela cheia + toque, que funciona
> offline. No iOS a Apple não permite tela cheia, então vira uma notificação "urgente".

## Como rodar
Precisa do [Flutter](https://docs.flutter.dev/get-started/install) instalado.

```bash
bash tool/setup.sh     # gera android/ e ios/, aplica permissões e baixa pacotes
flutter run            # com o celular conectado
flutter build apk --release
```

Sem Flutter instalado: o workflow `.github/workflows/build-apk.yml` compila o APK no GitHub
(aba Actions → artefato `prazo-apk`).

## Primeiro uso
Abra **Configurações → Testar ligação**, conceda as permissões (notificações, alarmes exatos, tela cheia)
e bloqueie a tela. Em Xiaomi/Samsung/Huawei, desative a otimização de bateria para o app.


## Três versões (APKs)

| APK | Para quê | Rede |
|---|---|---|
| `prazo-normal.apk` | Celulares comuns. Várias contas, digital, tarefas. Pode ser pareado com o Dev. | Só a rede wi-fi local (nada de internet) |
| `prazo-dev.apk` | O seu celular. Acha os celulares normais no wi-fi e sincroniza contas e tarefas. | Só a rede wi-fi local |
| `prazo-online.apk` | Sincroniza pela internet com um servidor seu. | Internet (HTTPS) |

Os três podem ficar instalados juntos (ids diferentes).

### Sincronização na rede local (normal ↔ dev)
1. No celular normal: Configurações → Sincronização → **Permitir um novo aparelho** (mostra um código de uso único, vale 5 min).
2. No Dev: Sincronização → **Procurar** → Parear → digite o código. No normal, confirme o pedido.
3. Pronto: contas, tarefas, categorias e exclusões ficam iguais nos dois. Mexeu em um, o outro atualiza em poucos segundos;
   se um estiver fora da rede, sincroniza sozinho quando voltar. Em conflito vale a edição mais recente (confira se os relógios estão certos).

Segurança: tudo é cifrado com AES-256-GCM; o código passa por PBKDF2 (100 mil iterações) e só serve para trocar uma
chave aleatória de 256 bits; o código expira em 5 min, vale uma vez e trava após 5 erros; o dono do celular normal
precisa aprovar; mensagens têm horário e são recusadas se repetidas; dá para revogar cada aparelho. O servidor só
atende a rede local. A sincronização só roda com o app aberto (o Android pausa apps em segundo plano).

### Versão online
Suba `server/server.py` atrás de HTTPS (ex.: Caddy ou Cloudflare Tunnel):
`python3 server/server.py --port 8080 --data ./dados`. No app: endereço `https://…` + uma frase secreta de 12+ caracteres,
igual em todos os aparelhos. O servidor só guarda blocos cifrados; a frase nunca sai do celular.

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

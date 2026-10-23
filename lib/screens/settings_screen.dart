import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/notification_service.dart';
import '../services/task_store.dart';
import '../utils.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const _callOptions = [5, 10, 15, 30, 60];
  static const _reminderOptions = [1440, 120, 60, 30, 10, 0];

  @override
  Widget build(BuildContext context) {
    final s = context.watch<TaskStore>();
    return Scaffold(
      appBar: AppBar(title: const Text('Configurações')),
      body: ListView(
        children: [
          const _Header('Padrões para novas tarefas'),
          SwitchListTile(
            title: const Text('Ligar antes de vencer'),
            value: s.callByDefault,
            onChanged: (v) => s.updateSettings(callByDefault: v),
          ),
          ListTile(
            title: const Text('Ligar quantos minutos antes'),
            trailing: DropdownButton<int>(
              value: _callOptions.contains(s.defaultCallMinutes)
                  ? s.defaultCallMinutes
                  : null,
              items: [
                for (final m in _callOptions)
                  DropdownMenuItem(value: m, child: Text('$m min')),
              ],
              onChanged: (v) => s.updateSettings(defaultCallMinutes: v),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(spacing: 8, children: [
              for (final m in _reminderOptions)
                FilterChip(
                  label: Text(minutesLabel(m)),
                  selected: s.defaultReminders.contains(m),
                  onSelected: (v) {
                    final l = [...s.defaultReminders];
                    v ? l.add(m) : l.remove(m);
                    s.updateSettings(defaultReminders: l);
                  },
                ),
            ]),
          ),
          const Divider(height: 32),
          const _Header('Alertas'),
          ListTile(
            leading: const Icon(Icons.ring_volume),
            title: const Text('Testar ligação'),
            subtitle: const Text(
                'Toca em 10 segundos — bloqueie a tela para ver como fica'),
            onTap: () async {
              await NotificationService.instance.requestPermissions();
              await NotificationService.instance.scheduleTestCall();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                    content: Text('A ligação de teste toca em 10 segundos')));
              }
            },
          ),
          ListTile(
            leading: const Icon(Icons.security),
            title: const Text('Conceder permissões'),
            subtitle: const Text(
                'Notificações, alarmes exatos e notificações em tela cheia'),
            onTap: () => NotificationService.instance.requestPermissions(),
          ),
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'Dica: em alguns celulares (Xiaomi, Samsung, Huawei…) é preciso '
              'desativar a otimização de bateria para o Prazo e permitir '
              '“Exibir sobre outros apps”/“Notificações em tela cheia” nas '
              'configurações do sistema, senão o alerta pode atrasar.',
              style: TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final String text;
  const _Header(this.text);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
        child: Text(text,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(color: Theme.of(context).colorScheme.primary)),
      );
}

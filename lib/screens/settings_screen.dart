import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/notification_service.dart';
import '../services/task_store.dart';
import '../utils.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  static const _callOptions = [5, 10, 15, 30, 60];
  static const _reminderOptions = [1440, 120, 60, 30, 10, 0];

  Future<void> _addCategory(BuildContext context, TaskStore s) async {
    final c = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nova categoria'),
        content: TextField(
            controller: c,
            autofocus: true,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: 'Nome')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, c.text.trim()),
              child: const Text('Adicionar')),
        ],
      ),
    );
    if (name != null) await s.addCategory(name);
  }

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
          const _Header('Categorias'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(spacing: 8, children: [
              for (final c in s.categories)
                InputChip(label: Text(c), onDeleted: () => s.removeCategory(c)),
              ActionChip(
                avatar: const Icon(Icons.add, size: 18),
                label: const Text('Nova'),
                onPressed: () => _addCategory(context, s),
              ),
            ]),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Text(
                'Remover uma categoria só a tira da lista de opções. '
                'As tarefas que já a usam (concluídas ou futuras) continuam como estão.',
                style: TextStyle(fontSize: 12)),
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

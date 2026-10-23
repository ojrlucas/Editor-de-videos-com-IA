import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/task.dart';
import '../services/task_store.dart';
import '../utils.dart';

class StatsScreen extends StatelessWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final tasks = context.watch<TaskStore>().tasks;
    final done = tasks.where((t) => t.done).length;
    final overdue = tasks.where((t) => t.isOverdue).length;
    final pending = tasks.length - done;
    final rate = tasks.isEmpty ? 0.0 : done / tasks.length;

    final today = dayOnly(DateTime.now());
    final days = [for (var i = 6; i >= 0; i--) today.subtract(Duration(days: i))];
    final perDay = [
      for (final d in days)
        tasks.where((t) => t.doneAt != null && dayOnly(t.doneAt!) == d).length
    ];
    final maxDay = perDay.fold<int>(1, (a, b) => b > a ? b : a);

    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Estatísticas')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(children: [
            _Stat('Pendentes', '$pending', scheme.primary),
            _Stat('Atrasadas', '$overdue', scheme.error),
            _Stat('Concluídas', '$done', Colors.green),
          ]),
          const SizedBox(height: 24),
          Text('Taxa de conclusão: ${(rate * 100).round()}%'),
          const SizedBox(height: 8),
          LinearProgressIndicator(value: rate, minHeight: 10),
          const SizedBox(height: 32),
          Text('Concluídas nos últimos 7 dias',
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 16),
          SizedBox(
            height: 140,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (var i = 0; i < 7; i++)
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text('${perDay[i]}'),
                        const SizedBox(height: 4),
                        Container(
                          height: 90 * perDay[i] / maxDay + 4,
                          margin: const EdgeInsets.symmetric(horizontal: 6),
                          decoration: BoxDecoration(
                            color: scheme.primary,
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(DateFormat.E('pt_BR').format(days[i]).substring(0, 3),
                            style: const TextStyle(fontSize: 12)),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          Text('Pendentes por prioridade',
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          for (final p in TaskPriority.values.reversed)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.flag,
                  color: switch (p) {
                    TaskPriority.high => Colors.red,
                    TaskPriority.medium => Colors.orange,
                    TaskPriority.low => Colors.green,
                  }),
              title: Text(p.label),
              trailing:
                  Text('${tasks.where((t) => !t.done && t.priority == p).length}'),
            ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  final String label, value;
  final Color color;
  const _Stat(this.label, this.value, this.color);

  @override
  Widget build(BuildContext context) => Expanded(
        child: Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Column(children: [
              Text(value,
                  style: TextStyle(
                      fontSize: 32, fontWeight: FontWeight.bold, color: color)),
              Text(label),
            ]),
          ),
        ),
      );
}

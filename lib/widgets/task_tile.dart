import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/task.dart';
import '../services/task_store.dart';
import '../utils.dart';

Color priorityColor(TaskPriority p) => switch (p) {
      TaskPriority.low => Colors.green,
      TaskPriority.medium => Colors.orange,
      TaskPriority.high => Colors.red,
    };

class TaskTile extends StatelessWidget {
  final Task task;
  final VoidCallback onTap;
  const TaskTile({super.key, required this.task, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final store = context.read<TaskStore>();
    final scheme = Theme.of(context).colorScheme;
    final t = task;
    final dueColor = t.isOverdue
        ? scheme.error
        : (!t.done && t.due.difference(DateTime.now()).inMinutes < 60)
            ? Colors.orange.shade800
            : scheme.onSurfaceVariant;

    return Dismissible(
      key: ValueKey('dismiss_${t.id}'),
      background: Container(
        color: Colors.green,
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(left: 24),
        child: const Icon(Icons.check, color: Colors.white),
      ),
      secondaryBackground: Container(
        color: scheme.error,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 24),
        child: const Icon(Icons.delete_outline, color: Colors.white),
      ),
      confirmDismiss: (dir) async {
        final messenger = ScaffoldMessenger.of(context);
        messenger.hideCurrentSnackBar();
        if (dir == DismissDirection.startToEnd) {
          final wasDone = t.done;
          await store.setDone(t, !wasDone);
          messenger.showSnackBar(SnackBar(
            content: Text(wasDone ? 'Tarefa reaberta' : 'Tarefa concluída'),
            action: SnackBarAction(
                label: 'Desfazer', onPressed: () => store.setDone(t, wasDone)),
          ));
          return false; // o item some da lista pelo filtro, não pelo Dismissible
        }
        await store.remove(t);
        messenger.showSnackBar(SnackBar(
          content: const Text('Tarefa excluída'),
          action: SnackBarAction(
              label: 'Desfazer', onPressed: () => store.upsert(t)),
        ));
        return false;
      },
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 6, 16, 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 4,
                height: 56,
                margin: const EdgeInsets.only(left: 4, right: 4, top: 4),
                decoration: BoxDecoration(
                  color: priorityColor(t.priority),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Checkbox(
                value: t.done,
                shape: const CircleBorder(),
                onChanged: (v) => store.setDone(t, v ?? false),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        t.title,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              decoration:
                                  t.done ? TextDecoration.lineThrough : null,
                              color: t.done ? scheme.outline : null,
                            ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${relativeDue(t.due, done: t.done)}  ·  ${t.category}',
                        style: TextStyle(color: dueColor, fontSize: 13),
                      ),
                      if (t.subtasks.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Row(children: [
                          Expanded(
                            child: LinearProgressIndicator(
                                value: t.progress, minHeight: 4),
                          ),
                          const SizedBox(width: 8),
                          Text(
                              '${t.subtasks.where((s) => s.done).length}/${t.subtasks.length}',
                              style: const TextStyle(fontSize: 12)),
                        ]),
                      ],
                    ],
                  ),
                ),
              ),
              if (!t.done && t.callAlert)
                Padding(
                  padding: const EdgeInsets.only(top: 12, left: 8),
                  child: Tooltip(
                    message: 'Liga ${t.callMinutes} min antes',
                    child: Icon(Icons.ring_volume,
                        size: 20, color: scheme.primary),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

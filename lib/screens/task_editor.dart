import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/task.dart';
import '../services/task_store.dart';
import '../utils.dart';

class TaskEditor extends StatefulWidget {
  final Task? task;
  const TaskEditor({super.key, this.task});

  @override
  State<TaskEditor> createState() => _TaskEditorState();
}

class _TaskEditorState extends State<TaskEditor> {
  static const _reminderOptions = [1440, 120, 60, 30, 10, 0];
  static const _callOptions = [5, 10, 15, 30, 60];

  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _notes;
  final _subCtrl = TextEditingController();
  late DateTime _due;
  late TaskPriority _priority;
  late String _category;
  late List<SubTask> _subs;
  late Set<int> _reminders;
  late bool _call;
  late int _callMinutes;

  bool get _editing => widget.task != null;

  @override
  void initState() {
    super.initState();
    final t = widget.task;
    final s = context.read<TaskStore>();
    _title = TextEditingController(text: t?.title ?? '');
    _notes = TextEditingController(text: t?.notes ?? '');
    final now = DateTime.now();
    _due = t?.due ??
        DateTime(now.year, now.month, now.day, now.hour + 2);
    _priority = t?.priority ?? TaskPriority.medium;
    _category = t?.category ?? defaultCategories.first;
    _subs = t?.subtasks.map((e) => SubTask(e.title, done: e.done)).toList() ?? [];
    _reminders = {...(t?.reminders ?? s.defaultReminders)};
    _call = t?.callAlert ?? s.callByDefault;
    _callMinutes = t?.callMinutes ?? s.defaultCallMinutes;
  }

  @override
  void dispose() {
    _title.dispose();
    _notes.dispose();
    _subCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
      context: context,
      initialDate: _due,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365 * 5)),
    );
    if (d != null) {
      setState(() =>
          _due = DateTime(d.year, d.month, d.day, _due.hour, _due.minute));
    }
  }

  Future<void> _pickTime() async {
    final t = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_due),
      builder: (c, child) => MediaQuery(
        data: MediaQuery.of(c).copyWith(alwaysUse24HourFormat: true),
        child: child!,
      ),
    );
    if (t != null) {
      setState(() =>
          _due = DateTime(_due.year, _due.month, _due.day, t.hour, t.minute));
    }
  }

  void _quick(DateTime d) => setState(() => _due = d);

  void _addSub() {
    final v = _subCtrl.text.trim();
    if (v.isEmpty) return;
    setState(() {
      _subs.add(SubTask(v));
      _subCtrl.clear();
    });
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final store = context.read<TaskStore>();
    final old = widget.task;
    final task = Task(
      id: old?.id ?? store.newId(),
      title: _title.text.trim(),
      notes: _notes.text.trim(),
      due: _due,
      priority: _priority,
      category: _category,
      subtasks: _subs,
      reminders: _reminders.toList()..sort(),
      callAlert: _call,
      callMinutes: _callMinutes,
      done: old?.done ?? false,
      doneAt: old?.doneAt,
      createdAt: old?.createdAt,
    );
    await store.upsert(task);
    if (mounted) Navigator.of(context).pop();
  }

  Future<void> _delete() async {
    final store = context.read<TaskStore>();
    final t = widget.task!;
    final nav = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    await store.remove(t);
    nav.pop();
    messenger.showSnackBar(SnackBar(
      content: const Text('Tarefa excluída'),
      action: SnackBarAction(label: 'Desfazer', onPressed: () => store.upsert(t)),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final categories = {
      ...defaultCategories,
      if (!defaultCategories.contains(_category)) _category,
    }.toList();

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing ? 'Editar tarefa' : 'Nova tarefa'),
        actions: [
          if (_editing)
            IconButton(
                icon: const Icon(Icons.delete_outline), onPressed: _delete),
          TextButton(onPressed: _save, child: const Text('Salvar')),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _title,
              autofocus: !_editing,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                  labelText: 'O que precisa ser feito?',
                  border: OutlineInputBorder()),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Dê um título' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _notes,
              maxLines: 3,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                  labelText: 'Anotações (opcional)',
                  border: OutlineInputBorder()),
            ),
            const _Section('Prazo'),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.calendar_today, size: 18),
                  label: Text(fullDue(_due).split(' · ').first),
                  onPressed: _pickDate,
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                icon: const Icon(Icons.schedule, size: 18),
                label: Text(fullDue(_due).split(' · ').last),
                onPressed: _pickTime,
              ),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 8, children: [
              ActionChip(
                  label: const Text('Daqui a 1 h'),
                  onPressed: () => _quick(now.add(const Duration(hours: 1)))),
              ActionChip(
                  label: const Text('Hoje 18h'),
                  onPressed: () => _quick(today.add(const Duration(hours: 18)))),
              ActionChip(
                  label: const Text('Amanhã 9h'),
                  onPressed: () => _quick(
                      today.add(const Duration(days: 1, hours: 9)))),
              ActionChip(
                  label: const Text('Próx. semana'),
                  onPressed: () => _quick(DateTime(_due.year, _due.month,
                      _due.day + 7, _due.hour, _due.minute))),
            ]),
            if (_due.isBefore(now))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text('Esse horário já passou — nenhum alerta será disparado.',
                    style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            const _Section('Prioridade'),
            SegmentedButton<TaskPriority>(
              segments: [
                for (final p in TaskPriority.values)
                  ButtonSegment(value: p, label: Text(p.label)),
              ],
              selected: {_priority},
              onSelectionChanged: (s) => setState(() => _priority = s.first),
            ),
            const _Section('Categoria'),
            Wrap(spacing: 8, children: [
              for (final c in categories)
                ChoiceChip(
                  label: Text(c),
                  selected: _category == c,
                  onSelected: (_) => setState(() => _category = c),
                ),
            ]),
            const _Section('Lembretes'),
            Wrap(spacing: 8, children: [
              for (final m in _reminderOptions)
                FilterChip(
                  label: Text(minutesLabel(m)),
                  selected: _reminders.contains(m),
                  onSelected: (v) =>
                      setState(() => v ? _reminders.add(m) : _reminders.remove(m)),
                ),
            ]),
            const SizedBox(height: 8),
            Card(
              margin: EdgeInsets.zero,
              child: Column(children: [
                SwitchListTile(
                  secondary: const Icon(Icons.ring_volume),
                  title: const Text('Me ligar antes de vencer'),
                  subtitle: const Text(
                      'Tela cheia + toque insistente, até mesmo com o celular bloqueado'),
                  value: _call,
                  onChanged: (v) => setState(() => _call = v),
                ),
                if (_call)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                    child: Row(children: [
                      const Text('Ligar'),
                      const SizedBox(width: 12),
                      DropdownButton<int>(
                        value: _callOptions.contains(_callMinutes)
                            ? _callMinutes
                            : null,
                        items: [
                          for (final m in _callOptions)
                            DropdownMenuItem(
                                value: m, child: Text('$m min antes')),
                        ],
                        onChanged: (v) =>
                            setState(() => _callMinutes = v ?? _callMinutes),
                      ),
                    ]),
                  ),
              ]),
            ),
            const _Section('Subtarefas'),
            for (var i = 0; i < _subs.length; i++)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Checkbox(
                  value: _subs[i].done,
                  onChanged: (v) => setState(() => _subs[i].done = v ?? false),
                ),
                title: Text(_subs[i].title,
                    style: TextStyle(
                        decoration:
                            _subs[i].done ? TextDecoration.lineThrough : null)),
                trailing: IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => setState(() => _subs.removeAt(i)),
                ),
              ),
            Row(children: [
              Expanded(
                child: TextField(
                  controller: _subCtrl,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: const InputDecoration(
                      hintText: 'Adicionar subtarefa'),
                  onSubmitted: (_) => _addSub(),
                ),
              ),
              IconButton(icon: const Icon(Icons.add_circle), onPressed: _addSub),
            ]),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String text;
  const _Section(this.text);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(text, style: Theme.of(context).textTheme.titleSmall),
      );
}

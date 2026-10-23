import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/task.dart';
import '../services/notification_service.dart';
import '../services/task_store.dart';
import '../utils.dart';
import '../widgets/task_tile.dart';
import 'settings_screen.dart';
import 'stats_screen.dart';
import 'task_editor.dart';

enum _Filter { all, today, upcoming, overdue, done }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  _Filter _filter = _Filter.all;
  String? _category;
  String _query = '';
  bool _searching = false;
  Timer? _clock;

  @override
  void initState() {
    super.initState();
    // Atualiza os textos "vence em…" e o estado de atraso a cada minuto.
    _clock = Timer.periodic(const Duration(minutes: 1), (_) {
      if (mounted) setState(() {});
    });
    WidgetsBinding.instance.addPostFrameCallback(
        (_) => NotificationService.instance.requestPermissions());
  }

  @override
  void dispose() {
    _clock?.cancel();
    super.dispose();
  }

  static const _filterLabels = {
    _Filter.all: 'Todas',
    _Filter.today: 'Hoje',
    _Filter.upcoming: 'Próximas',
    _Filter.overdue: 'Atrasadas',
    _Filter.done: 'Concluídas',
  };

  bool _matches(Task t) {
    final today = dayOnly(DateTime.now());
    final d = dayOnly(t.due);
    final okFilter = switch (_filter) {
      _Filter.all => !t.done,
      _Filter.today => !t.done && d == today,
      _Filter.upcoming => !t.done && d.isAfter(today),
      _Filter.overdue => t.isOverdue,
      _Filter.done => t.done,
    };
    final q = _query.trim().toLowerCase();
    return okFilter &&
        (_category == null || t.category == _category) &&
        (q.isEmpty ||
            t.title.toLowerCase().contains(q) ||
            t.notes.toLowerCase().contains(q));
  }

  String _group(Task t) {
    if (t.done) return 'Concluídas';
    if (t.isOverdue) return 'Atrasadas';
    final diff = dayOnly(t.due).difference(dayOnly(DateTime.now())).inDays;
    if (diff == 0) return 'Hoje';
    if (diff == 1) return 'Amanhã';
    if (diff < 7) return 'Esta semana';
    return 'Mais adiante';
  }

  void _open([Task? t]) => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => TaskEditor(task: t)));

  @override
  Widget build(BuildContext context) {
    final store = context.watch<TaskStore>();
    final items = store.tasks.where(_matches).toList()
      ..sort((a, b) {
        if (_filter == _Filter.done) {
          return (b.doneAt ?? b.due).compareTo(a.doneAt ?? a.due);
        }
        final c = a.due.compareTo(b.due);
        return c != 0 ? c : b.priority.index.compareTo(a.priority.index);
      });

    final categories = {
      ...defaultCategories,
      ...store.tasks.map((t) => t.category),
    }.toList();

    final overdueCount = store.tasks.where((t) => t.isOverdue).length;

    // Constrói a lista com cabeçalhos de grupo.
    final children = <Widget>[];
    String? last;
    for (final t in items) {
      final g = _group(t);
      if (g != last) {
        children.add(Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 4),
          child: Text(g,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: g == 'Atrasadas'
                      ? Theme.of(context).colorScheme.error
                      : Theme.of(context).colorScheme.primary)),
        ));
        last = g;
      }
      children.add(TaskTile(
        key: ValueKey(t.id),
        task: t,
        onTap: () => _open(t),
      ));
    }

    return Scaffold(
      appBar: AppBar(
        title: _searching
            ? TextField(
                autofocus: true,
                decoration: const InputDecoration(
                    hintText: 'Buscar tarefa…', border: InputBorder.none),
                onChanged: (v) => setState(() => _query = v),
              )
            : const Text('Prazo'),
        actions: [
          IconButton(
            icon: Icon(_searching ? Icons.close : Icons.search),
            onPressed: () => setState(() {
              _searching = !_searching;
              if (!_searching) _query = '';
            }),
          ),
          PopupMenuButton<String>(
            icon: Icon(Icons.label_outline,
                color: _category == null
                    ? null
                    : Theme.of(context).colorScheme.primary),
            tooltip: 'Categoria',
            onSelected: (v) => setState(() => _category = v.isEmpty ? null : v),
            itemBuilder: (_) => [
              const PopupMenuItem(value: '', child: Text('Todas as categorias')),
              for (final c in categories) PopupMenuItem(value: c, child: Text(c)),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.insights_outlined),
            tooltip: 'Estatísticas',
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const StatsScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Configurações',
            onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SettingsScreen())),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(52),
          child: SizedBox(
            height: 52,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                for (final f in _Filter.values)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(f == _Filter.overdue && overdueCount > 0
                          ? '${_filterLabels[f]} ($overdueCount)'
                          : _filterLabels[f]!),
                      selected: _filter == f,
                      onSelected: (_) => setState(() => _filter = f),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
      body: items.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.task_alt,
                        size: 72, color: Theme.of(context).colorScheme.outline),
                    const SizedBox(height: 12),
                    Text(
                        _filter == _Filter.done
                            ? 'Nada concluído ainda.'
                            : 'Nenhuma tarefa por aqui. Toque em “Nova tarefa”.',
                        textAlign: TextAlign.center),
                  ],
                ),
              ),
            )
          : ListView(
              padding: const EdgeInsets.only(bottom: 96),
              children: children,
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(),
        icon: const Icon(Icons.add),
        label: const Text('Nova tarefa'),
      ),
    );
  }
}

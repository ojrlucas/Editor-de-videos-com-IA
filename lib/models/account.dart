import 'package:flutter/material.dart';

import '../utils.dart';
import 'task.dart';

const accountColors = [
  Color(0xFF4F46E5),
  Color(0xFF0D9488),
  Color(0xFFDB2777),
  Color(0xFFEA580C),
  Color(0xFF2563EB),
  Color(0xFF65A30D),
];

class Account {
  final String id;
  String name;
  int color;
  int updatedAt;

  Account({required this.id, required this.name, this.color = 0, int? updatedAt})
      : updatedAt = updatedAt ?? nowMs();

  Color get tint => accountColors[color % accountColors.length];
  String get initial => name.trim().isEmpty ? '?' : name.trim()[0].toUpperCase();

  Map<String, dynamic> toJson() =>
      {'id': id, 'name': name, 'color': color, 'updatedAt': updatedAt};
  factory Account.fromJson(Map<String, dynamic> j) => Account(
      id: j['id'] as String,
      name: j['name'] as String,
      color: j['color'] as int? ?? 0,
      updatedAt: j['updatedAt'] as int? ?? 0);
}

/// Tudo o que pertence a uma conta, em memória, com regra de mesclagem.
class AccountData {
  Account account;
  List<Task> tasks;

  /// uid da tarefa apagada -> hora da exclusão (impede que ela "volte" ao sincronizar).
  Map<String, int> tombs;
  List<String> categories;
  int categoriesAt;
  bool callByDefault;
  int defaultCallMinutes;
  List<int> defaultReminders;
  int settingsAt;

  AccountData({
    required this.account,
    List<Task>? tasks,
    Map<String, int>? tombs,
    List<String>? categories,
    this.categoriesAt = 0,
    this.callByDefault = true,
    this.defaultCallMinutes = 10,
    List<int>? defaultReminders,
    this.settingsAt = 0,
  })  : tasks = tasks ?? [],
        tombs = tombs ?? {},
        categories = categories ?? [...defaultCategories],
        defaultReminders = defaultReminders ?? [60, 0];

  Map<String, dynamic> toJson() => {
        'account': account.toJson(),
        'tasks': tasks.map((t) => t.toJson()).toList(),
        'tombs': tombs,
        'categories': categories,
        'categoriesAt': categoriesAt,
        'callByDefault': callByDefault,
        'defaultCallMinutes': defaultCallMinutes,
        'defaultReminders': defaultReminders,
        'settingsAt': settingsAt,
      };

  factory AccountData.fromJson(Map<String, dynamic> j) => AccountData(
        account: Account.fromJson(Map<String, dynamic>.from(j['account'] as Map)),
        tasks: (j['tasks'] as List? ?? [])
            .map((e) => Task.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
        tombs: {
          for (final e in (j['tombs'] as Map? ?? {}).entries)
            e.key as String: (e.value as num).toInt()
        },
        categories: (j['categories'] as List?)?.cast<String>(),
        categoriesAt: j['categoriesAt'] as int? ?? 0,
        callByDefault: j['callByDefault'] as bool? ?? true,
        defaultCallMinutes: j['defaultCallMinutes'] as int? ?? 10,
        defaultReminders: (j['defaultReminders'] as List?)?.cast<int>(),
        settingsAt: j['settingsAt'] as int? ?? 0,
      );

  /// Mescla [o] aqui: por tarefa vence a edição mais recente; exclusões valem
  /// se forem mais novas que a última edição. Retorna true se algo mudou.
  bool merge(AccountData o, int Function() newId) {
    var changed = false;
    if (o.account.updatedAt > account.updatedAt) {
      account
        ..name = o.account.name
        ..color = o.account.color
        ..updatedAt = o.account.updatedAt;
      changed = true;
    }
    for (final e in o.tombs.entries) {
      if ((tombs[e.key] ?? 0) < e.value) {
        tombs[e.key] = e.value;
        changed = true;
      }
    }
    for (final r in o.tasks) {
      final tomb = tombs[r.uid];
      if (tomb != null && tomb >= r.updatedAt) continue;
      final i = tasks.indexWhere((t) => t.uid == r.uid);
      if (i < 0) {
        r.id = newId();
        tasks.add(r);
        changed = true;
      } else if (r.updatedAt > tasks[i].updatedAt) {
        tasks[i].assign(r);
        changed = true;
      }
    }
    final before = tasks.length;
    tasks.removeWhere((t) {
      final tomb = tombs[t.uid];
      return tomb != null && tomb >= t.updatedAt;
    });
    if (tasks.length != before) changed = true;

    if (o.categoriesAt > categoriesAt) {
      categories = [...o.categories];
      categoriesAt = o.categoriesAt;
      changed = true;
    }
    if (o.settingsAt > settingsAt) {
      callByDefault = o.callByDefault;
      defaultCallMinutes = o.defaultCallMinutes;
      defaultReminders = [...o.defaultReminders];
      settingsAt = o.settingsAt;
      changed = true;
    }
    return changed;
  }
}

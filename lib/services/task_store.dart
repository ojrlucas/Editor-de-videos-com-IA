import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/task.dart';
import 'notification_service.dart';

class TaskStore extends ChangeNotifier {
  static const _tasksKey = 'tasks_v1';
  static const _settingsKey = 'settings_v1';

  late SharedPreferences _prefs;
  final List<Task> _tasks = [];
  int _nextId = 1;

  // Configurações padrão para novas tarefas.
  bool callByDefault = true;
  int defaultCallMinutes = 10;
  List<int> defaultReminders = [60, 0];

  List<Task> get tasks => List.unmodifiable(_tasks);
  Task? byId(int id) {
    for (final t in _tasks) {
      if (t.id == id) return t;
    }
    return null;
  }

  Future<void> load() async {
    _prefs = await SharedPreferences.getInstance();
    final raw = _prefs.getString(_tasksKey);
    if (raw != null) {
      for (final e in jsonDecode(raw) as List) {
        _tasks.add(Task.fromJson(Map<String, dynamic>.from(e as Map)));
      }
    }
    final s = _prefs.getString(_settingsKey);
    if (s != null) {
      final m = jsonDecode(s) as Map<String, dynamic>;
      _nextId = m['nextId'] as int? ?? 1;
      callByDefault = m['callByDefault'] as bool? ?? true;
      defaultCallMinutes = m['defaultCallMinutes'] as int? ?? 10;
      defaultReminders = (m['defaultReminders'] as List? ?? [60, 0]).cast<int>();
    }
    for (final t in _tasks) {
      if (t.id >= _nextId) _nextId = t.id + 1;
    }
    // Garante que os alarmes batem com os dados (ex.: após reinstalar/reiniciar).
    for (final t in _tasks) {
      await NotificationService.instance.scheduleTask(t);
    }
  }

  int newId() => _nextId++;

  Future<void> _save() async {
    await _prefs.setString(
        _tasksKey, jsonEncode(_tasks.map((t) => t.toJson()).toList()));
    await _prefs.setString(
        _settingsKey,
        jsonEncode({
          'nextId': _nextId,
          'callByDefault': callByDefault,
          'defaultCallMinutes': defaultCallMinutes,
          'defaultReminders': defaultReminders,
        }));
  }

  Future<void> _commit(Task? t) async {
    if (t != null) await NotificationService.instance.scheduleTask(t);
    await _save();
    notifyListeners();
  }

  Future<void> upsert(Task t) async {
    final i = _tasks.indexWhere((e) => e.id == t.id);
    if (i >= 0) {
      _tasks[i] = t;
    } else {
      _tasks.add(t);
    }
    await _commit(t);
  }

  Future<void> remove(Task t) async {
    _tasks.removeWhere((e) => e.id == t.id);
    await NotificationService.instance.cancelTask(t.id);
    await _commit(null);
  }

  Future<void> setDone(Task t, bool done) async {
    t.done = done;
    t.doneAt = done ? DateTime.now() : null;
    if (done) {
      for (final s in t.subtasks) {
        s.done = true;
      }
    }
    await _commit(t);
  }

  Future<void> toggleSubtask(Task t, SubTask s) async {
    s.done = !s.done;
    await _commit(null);
  }

  Future<void> snoozeCall(Task t, int minutes) async {
    await NotificationService.instance.snoozeCall(t, minutes);
  }

  Future<void> updateSettings({
    bool? callByDefault,
    int? defaultCallMinutes,
    List<int>? defaultReminders,
  }) async {
    this.callByDefault = callByDefault ?? this.callByDefault;
    this.defaultCallMinutes = defaultCallMinutes ?? this.defaultCallMinutes;
    this.defaultReminders = defaultReminders ?? this.defaultReminders;
    await _commit(null);
  }
}

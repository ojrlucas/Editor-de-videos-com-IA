import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/account.dart';
import '../models/task.dart';
import 'notification_service.dart';

/// Guarda contas, tarefas e configurações. Cada conta tem seus próprios dados;
/// só a conta ativa tem alarmes agendados.
class TaskStore extends ChangeNotifier {
  static const _accountsKey = 'accounts_v1';
  static const _activeKey = 'active_account_v1';
  static const _nextIdKey = 'next_id_v1';

  late SharedPreferences _prefs;
  final List<Task> _tasks = [];
  final List<Account> _accounts = [];
  late Account _active;
  int _nextId = 1;

  // Configurações da conta ativa.
  bool callByDefault = true;
  int defaultCallMinutes = 10;
  List<int> defaultReminders = [60, 0];
  List<String> categories = [...defaultCategories];

  List<Task> get tasks => List.unmodifiable(_tasks);
  List<Account> get accounts => List.unmodifiable(_accounts);
  Account get active => _active;

  Task? byId(int id) {
    for (final t in _tasks) {
      if (t.id == id) return t;
    }
    return null;
  }

  String get _tasksKey => 'tasks_v1_${_active.id}';
  String get _settingsKey => 'settings_v1_${_active.id}';

  Future<void> load() async {
    _prefs = await SharedPreferences.getInstance();

    final rawAccounts = _prefs.getString(_accountsKey);
    if (rawAccounts != null) {
      for (final e in jsonDecode(rawAccounts) as List) {
        _accounts.add(Account.fromJson(Map<String, dynamic>.from(e as Map)));
      }
    }
    if (_accounts.isEmpty) {
      _accounts.add(Account(id: 'a1', name: 'Minha conta'));
      // Migra os dados da versão sem contas.
      final legacyTasks = _prefs.getString('tasks_v1');
      if (legacyTasks != null) await _prefs.setString('tasks_v1_a1', legacyTasks);
      final legacySettings = _prefs.getString('settings_v1');
      if (legacySettings != null) {
        await _prefs.setString('settings_v1_a1', legacySettings);
      }
    }
    final activeId = _prefs.getString(_activeKey);
    _active = _accounts.firstWhere((a) => a.id == activeId,
        orElse: () => _accounts.first);

    _nextId = _prefs.getInt(_nextIdKey) ?? 1;
    await _loadActive();
    await _saveAccounts();
  }

  Future<void> _loadActive() async {
    _tasks.clear();
    final raw = _prefs.getString(_tasksKey);
    if (raw != null) {
      for (final e in jsonDecode(raw) as List) {
        _tasks.add(Task.fromJson(Map<String, dynamic>.from(e as Map)));
      }
    }
    callByDefault = true;
    defaultCallMinutes = 10;
    defaultReminders = [60, 0];
    categories = [...defaultCategories];
    final s = _prefs.getString(_settingsKey);
    if (s != null) {
      final m = jsonDecode(s) as Map<String, dynamic>;
      callByDefault = m['callByDefault'] as bool? ?? true;
      defaultCallMinutes = m['defaultCallMinutes'] as int? ?? 10;
      defaultReminders = (m['defaultReminders'] as List? ?? [60, 0]).cast<int>();
      categories = (m['categories'] as List? ?? defaultCategories).cast<String>();
      final legacyNext = m['nextId'] as int?;
      if (legacyNext != null && legacyNext > _nextId) _nextId = legacyNext;
    }
    for (final t in _tasks) {
      if (t.id >= _nextId) _nextId = t.id + 1;
    }
    // Garante que os alarmes batem com os dados (após reinstalar/reiniciar).
    for (final t in _tasks) {
      await NotificationService.instance.scheduleTask(t);
    }
  }

  int newId() {
    final id = _nextId++;
    _prefs.setInt(_nextIdKey, _nextId);
    return id;
  }

  Future<void> _saveAccounts() async {
    await _prefs.setString(
        _accountsKey, jsonEncode(_accounts.map((a) => a.toJson()).toList()));
    await _prefs.setString(_activeKey, _active.id);
    await _prefs.setInt(_nextIdKey, _nextId);
  }

  Future<void> _save() async {
    await _prefs.setString(
        _tasksKey, jsonEncode(_tasks.map((t) => t.toJson()).toList()));
    await _prefs.setString(
        _settingsKey,
        jsonEncode({
          'callByDefault': callByDefault,
          'defaultCallMinutes': defaultCallMinutes,
          'defaultReminders': defaultReminders,
          'categories': categories,
        }));
    await _prefs.setInt(_nextIdKey, _nextId);
  }

  Future<void> _commit(Task? t) async {
    if (t != null) await NotificationService.instance.scheduleTask(t);
    await _save();
    notifyListeners();
  }

  // ---- contas ------------------------------------------------------------

  Future<void> switchAccount(String id) async {
    if (id == _active.id) return;
    final target = _accounts.firstWhere((a) => a.id == id);
    for (final t in _tasks) {
      await NotificationService.instance.cancelTask(t.id);
    }
    await _save();
    _active = target;
    await _loadActive();
    await _saveAccounts();
    notifyListeners();
  }

  Future<Account> addAccount(String name) async {
    final a = Account(
        id: 'a${DateTime.now().microsecondsSinceEpoch}',
        name: name.trim(),
        color: _accounts.length % accountColors.length);
    _accounts.add(a);
    await _saveAccounts();
    notifyListeners();
    return a;
  }

  Future<void> renameAccount(Account a, String name) async {
    a.name = name.trim();
    await _saveAccounts();
    notifyListeners();
  }

  /// A conta ativa não pode ser removida; sempre sobra ao menos uma.
  Future<bool> removeAccount(Account a) async {
    if (a.id == _active.id || _accounts.length < 2) return false;
    _accounts.removeWhere((e) => e.id == a.id);
    await _prefs.remove('tasks_v1_${a.id}');
    await _prefs.remove('settings_v1_${a.id}');
    await _saveAccounts();
    notifyListeners();
    return true;
  }

  // ---- tarefas -----------------------------------------------------------

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

  // ---- categorias --------------------------------------------------------

  Future<void> addCategory(String name) async {
    final n = name.trim();
    if (n.isEmpty || categories.contains(n)) return;
    categories = [...categories, n];
    await _commit(null);
  }

  /// Remove só da lista de opções. Tarefas existentes mantêm a categoria.
  Future<void> removeCategory(String name) async {
    categories = categories.where((c) => c != name).toList();
    await _commit(null);
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

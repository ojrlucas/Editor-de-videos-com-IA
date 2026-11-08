import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/account.dart';
import '../models/task.dart';
import '../utils.dart';
import 'notification_service.dart';

/// Guarda todas as contas em memória. Só a conta ativa tem alarmes agendados.
class TaskStore extends ChangeNotifier {
  static const _key = 'data_v2';

  late SharedPreferences _prefs;
  final Map<String, AccountData> _data = {};
  final Map<String, int> _accountTombs = {};
  late String _activeId;
  int _nextId = 1;

  AccountData get _cur => _data[_activeId]!;

  List<Account> get accounts => [for (final d in _data.values) d.account];
  Account get active => _cur.account;
  List<Task> get tasks => List.unmodifiable(_cur.tasks);
  List<String> get categories => List.unmodifiable(_cur.categories);
  bool get callByDefault => _cur.callByDefault;
  int get defaultCallMinutes => _cur.defaultCallMinutes;
  List<int> get defaultReminders => List.unmodifiable(_cur.defaultReminders);

  Task? byId(int id) {
    for (final t in _cur.tasks) {
      if (t.id == id) return t;
    }
    return null;
  }

  int newId() => _nextId++;

  // ---- persistência ------------------------------------------------------

  Future<void> load() async {
    _prefs = await SharedPreferences.getInstance();
    final raw = _prefs.getString(_key);
    if (raw != null) {
      final m = jsonDecode(raw) as Map<String, dynamic>;
      for (final e in m['accounts'] as List) {
        final d = AccountData.fromJson(Map<String, dynamic>.from(e as Map));
        _data[d.account.id] = d;
      }
      for (final e in (m['accountTombs'] as Map? ?? {}).entries) {
        _accountTombs[e.key as String] = (e.value as num).toInt();
      }
      _activeId = m['active'] as String? ?? _data.keys.first;
      _nextId = m['nextId'] as int? ?? 1;
    } else {
      _migrateV1();
    }
    if (_data.isEmpty) {
      final a = Account(id: 'a${nowMs()}', name: 'Minha conta');
      _data[a.id] = AccountData(account: a);
    }
    if (!_data.containsKey(_activeId)) _activeId = _data.keys.first;
    for (final d in _data.values) {
      for (final t in d.tasks) {
        if (t.id >= _nextId) _nextId = t.id + 1;
      }
    }
    await _save();
    for (final t in _cur.tasks) {
      await NotificationService.instance.scheduleTask(t);
    }
  }

  /// Lê o formato antigo (uma chave por conta) e converte.
  void _migrateV1() {
    final accounts = <Account>[];
    final rawAccounts = _prefs.getString('accounts_v1');
    if (rawAccounts != null) {
      for (final e in jsonDecode(rawAccounts) as List) {
        accounts.add(Account.fromJson(Map<String, dynamic>.from(e as Map)));
      }
    }
    if (accounts.isEmpty) accounts.add(Account(id: 'a1', name: 'Minha conta'));
    for (final a in accounts) {
      final d = AccountData(account: a);
      final tasks = _prefs.getString('tasks_v1_${a.id}') ??
          (a.id == 'a1' ? _prefs.getString('tasks_v1') : null);
      if (tasks != null) {
        for (final e in jsonDecode(tasks) as List) {
          d.tasks.add(Task.fromJson(Map<String, dynamic>.from(e as Map)));
        }
      }
      final s = _prefs.getString('settings_v1_${a.id}') ??
          (a.id == 'a1' ? _prefs.getString('settings_v1') : null);
      if (s != null) {
        final m = jsonDecode(s) as Map<String, dynamic>;
        d.callByDefault = m['callByDefault'] as bool? ?? true;
        d.defaultCallMinutes = m['defaultCallMinutes'] as int? ?? 10;
        d.defaultReminders =
            (m['defaultReminders'] as List? ?? [60, 0]).cast<int>();
        d.categories = (m['categories'] as List?)?.cast<String>() ??
            [...defaultCategories];
        _nextId = (m['nextId'] as int?) ?? _nextId;
      }
      _data[a.id] = d;
    }
    _activeId = _prefs.getString('active_account_v1') ?? accounts.first.id;
    _nextId = _prefs.getInt('next_id_v1') ?? _nextId;
  }

  Future<void> _save() => _prefs.setString(
      _key,
      jsonEncode({
        'accounts': [for (final d in _data.values) d.toJson()],
        'accountTombs': _accountTombs,
        'active': _activeId,
        'nextId': _nextId,
      }));

  Future<void> _commit(Task? t) async {
    if (t != null) await NotificationService.instance.scheduleTask(t);
    await _save();
    notifyListeners();
  }

  // ---- sincronização -----------------------------------------------------

  Map<String, dynamic> exportSnapshot() => {
        'v': 1,
        'accounts': [for (final d in _data.values) d.toJson()],
        'accountTombs': _accountTombs,
      };

  /// Mescla o que veio de outro aparelho. Retorna true se algo mudou aqui.
  Future<bool> mergeSnapshot(Map<String, dynamic> snap) async {
    var changed = false;
    final idsBefore = {for (final t in _cur.tasks) t.id};

    for (final e in (snap['accountTombs'] as Map? ?? {}).entries) {
      final ts = (e.value as num).toInt();
      if ((_accountTombs[e.key as String] ?? 0) < ts) {
        _accountTombs[e.key as String] = ts;
        changed = true;
      }
    }
    for (final raw in (snap['accounts'] as List? ?? [])) {
      final r = AccountData.fromJson(Map<String, dynamic>.from(raw as Map));
      final tomb = _accountTombs[r.account.id];
      if (tomb != null && tomb >= r.account.updatedAt) continue;
      final local = _data[r.account.id];
      if (local == null) {
        for (final t in r.tasks) {
          t.id = newId();
        }
        _data[r.account.id] = r;
        changed = true;
      } else if (local.merge(r, newId)) {
        changed = true;
      }
    }
    for (final id in _data.keys.toList()) {
      final tomb = _accountTombs[id];
      if (tomb != null && id != _activeId && tomb >= _data[id]!.account.updatedAt) {
        _data.remove(id);
        changed = true;
      }
    }

    if (changed) {
      final ns = NotificationService.instance;
      final idsNow = {for (final t in _cur.tasks) t.id};
      for (final id in idsBefore.difference(idsNow)) {
        await ns.cancelTask(id);
      }
      for (final t in _cur.tasks) {
        await ns.scheduleTask(t);
      }
      await _save();
      notifyListeners();
    }
    return changed;
  }

  // ---- contas ------------------------------------------------------------

  Future<void> switchAccount(String id) async {
    if (id == _activeId || !_data.containsKey(id)) return;
    for (final t in _cur.tasks) {
      await NotificationService.instance.cancelTask(t.id);
    }
    _activeId = id;
    for (final t in _cur.tasks) {
      await NotificationService.instance.scheduleTask(t);
    }
    await _save();
    notifyListeners();
  }

  Future<Account> addAccount(String name) async {
    final a = Account(
        id: 'a${nowMs()}',
        name: name.trim(),
        color: _data.length % accountColors.length);
    _data[a.id] = AccountData(account: a);
    await _save();
    notifyListeners();
    return a;
  }

  Future<void> renameAccount(Account a, String name) async {
    a
      ..name = name.trim()
      ..updatedAt = nowMs();
    await _save();
    notifyListeners();
  }

  /// A conta ativa não pode ser removida; sempre sobra ao menos uma.
  Future<bool> removeAccount(Account a) async {
    if (a.id == _activeId || _data.length < 2) return false;
    _data.remove(a.id);
    _accountTombs[a.id] = nowMs();
    await _save();
    notifyListeners();
    return true;
  }

  // ---- tarefas -----------------------------------------------------------

  Future<void> upsert(Task t) async {
    t.updatedAt = nowMs();
    final list = _cur.tasks;
    final i = list.indexWhere((e) => e.id == t.id);
    if (i >= 0) {
      list[i] = t;
    } else {
      list.add(t);
    }
    await _commit(t);
  }

  Future<void> remove(Task t) async {
    _cur.tasks.removeWhere((e) => e.id == t.id);
    _cur.tombs[t.uid] = nowMs();
    await NotificationService.instance.cancelTask(t.id);
    await _commit(null);
  }

  Future<void> setDone(Task t, bool done) async {
    t.done = done;
    t.doneAt = done ? DateTime.now() : null;
    t.updatedAt = nowMs();
    if (done) {
      for (final s in t.subtasks) {
        s.done = true;
      }
    }
    await _commit(t);
  }

  Future<void> toggleSubtask(Task t, SubTask s) async {
    s.done = !s.done;
    t.updatedAt = nowMs();
    await _commit(null);
  }

  Future<void> snoozeCall(Task t, int minutes) async {
    await NotificationService.instance.snoozeCall(t, minutes);
  }

  // ---- categorias e configurações ----------------------------------------

  Future<void> addCategory(String name) async {
    final n = name.trim();
    if (n.isEmpty || _cur.categories.contains(n)) return;
    _cur.categories = [..._cur.categories, n];
    _cur.categoriesAt = nowMs();
    await _commit(null);
  }

  /// Remove só da lista de opções. Tarefas existentes mantêm a categoria.
  Future<void> removeCategory(String name) async {
    _cur.categories = _cur.categories.where((c) => c != name).toList();
    _cur.categoriesAt = nowMs();
    await _commit(null);
  }

  Future<void> updateSettings({
    bool? callByDefault,
    int? defaultCallMinutes,
    List<int>? defaultReminders,
  }) async {
    final d = _cur;
    d.callByDefault = callByDefault ?? d.callByDefault;
    d.defaultCallMinutes = defaultCallMinutes ?? d.defaultCallMinutes;
    d.defaultReminders = defaultReminders ?? d.defaultReminders;
    d.settingsAt = nowMs();
    await _commit(null);
  }
}

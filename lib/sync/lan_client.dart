import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import '../services/task_store.dart';
import 'crypto.dart';
import 'device.dart';
import 'lan_server.dart';

class LanPeer {
  final String ip;
  final String id;
  final String name;
  final bool pairing;
  final String? salt;
  LanPeer(this.ip, this.id, this.name, this.pairing, this.salt);
}

class SavedPeer {
  final String id;
  String name;
  String ip;
  final String key;
  int lastSync;
  bool online = false;
  SavedPeer(this.id, this.name, this.ip, this.key, [this.lastSync = 0]);

  Map<String, dynamic> toJson() =>
      {'id': id, 'name': name, 'ip': ip, 'key': key, 'lastSync': lastSync};
  factory SavedPeer.fromJson(Map<String, dynamic> j) => SavedPeer(
      j['id'] as String,
      j['name'] as String,
      j['ip'] as String,
      j['key'] as String,
      j['lastSync'] as int? ?? 0);
}

class _Resp {
  final int status;
  final Map<String, dynamic>? json;
  _Resp(this.status, this.json);
}

/// Cliente da versão Dev: acha os celulares na rede, pareia e sincroniza.
class LanClient extends ChangeNotifier with WidgetsBindingObserver {
  final TaskStore store;
  LanClient(this.store);

  final Map<String, SavedPeer> peers = {};
  bool autoSync = true;
  bool busy = false;
  String? status;
  Timer? _timer;
  Timer? _debounce;
  DateTime _lastScan = DateTime.fromMillisecondsSinceEpoch(0);

  Future<void> start() async {
    final raw = Device.prefs.getString('lan_peers_v1');
    if (raw != null) {
      for (final e in jsonDecode(raw) as List) {
        final p = SavedPeer.fromJson(Map<String, dynamic>.from(e as Map));
        peers[p.id] = p;
      }
    }
    autoSync = Device.prefs.getBool('lan_auto_v1') ?? true;
    WidgetsBinding.instance.addObserver(this);
    store.addListener(_onStoreChanged);
    _timer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (autoSync) syncAll();
    });
    if (autoSync) syncAll();
  }

  Future<void> setAuto(bool v) async {
    autoSync = v;
    await Device.prefs.setBool('lan_auto_v1', v);
    notifyListeners();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed && autoSync) syncAll();
  }

  /// Mexeu aqui -> manda para os outros logo em seguida.
  void _onStoreChanged() {
    if (busy || !autoSync || peers.isEmpty) return;
    _debounce?.cancel();
    _debounce = Timer(const Duration(seconds: 3), syncAll);
  }

  Future<void> _persist() => Device.prefs.setString(
      'lan_peers_v1', jsonEncode(peers.values.map((p) => p.toJson()).toList()));

  Future<void> forget(String id) async {
    peers.remove(id);
    await _persist();
    notifyListeners();
  }

  // ---- HTTP --------------------------------------------------------------

  Future<_Resp> _request(String ip, String path,
      {Map<String, dynamic>? body,
      Duration timeout = const Duration(seconds: 15)}) async {
    final c = HttpClient()..connectionTimeout = timeout;
    try {
      final uri = Uri.parse('http://$ip:${LanServer.port}$path');
      final req = await (body == null ? c.getUrl(uri) : c.postUrl(uri))
          .timeout(timeout);
      if (body != null) {
        req.headers.contentType = ContentType.json;
        req.add(utf8.encode(jsonEncode(body)));
      }
      final res = await req.close().timeout(timeout);
      final text = await utf8.decodeStream(res).timeout(timeout);
      Map<String, dynamic>? j;
      try {
        j = jsonDecode(text) as Map<String, dynamic>;
      } catch (_) {}
      return _Resp(res.statusCode, j);
    } catch (_) {
      return _Resp(0, null);
    } finally {
      c.close(force: true);
    }
  }

  Future<LanPeer?> _hello(String ip,
      [Duration t = const Duration(milliseconds: 700)]) async {
    final r = await _request(ip, '/hello', timeout: t);
    final j = r.json;
    if (r.status != 200 || j == null || j['app'] != 'prazo') return null;
    return LanPeer(ip, j['id'] as String, j['name'] as String,
        j['pairing'] == true, j['salt'] as String?);
  }

  Future<LanPeer?> helloPublic(String ip) => _hello(ip, const Duration(seconds: 3));

  /// Procura celulares com o app na mesma rede (varre o /24 de cada interface).
  Future<List<LanPeer>> scan() async {
    final found = <LanPeer>[];
    final ifaces = await NetworkInterface.list(
        type: InternetAddressType.IPv4, includeLoopback: false);
    final self = <String>{};
    final prefixes = <String>{};
    for (final i in ifaces) {
      for (final a in i.addresses) {
        self.add(a.address);
        final o = a.address.split('.');
        prefixes.add('${o[0]}.${o[1]}.${o[2]}');
      }
    }
    final ips = [
      for (final p in prefixes)
        for (var n = 1; n < 255; n++) '$p.$n'
    ]..removeWhere(self.contains);

    for (var i = 0; i < ips.length; i += 50) {
      final batch = ips.skip(i).take(50);
      final res = await Future.wait(batch.map(_hello));
      found.addAll(res.whereType<LanPeer>().where((p) => p.id != Device.id));
    }
    _lastScan = DateTime.now();
    return found;
  }

  // ---- pareamento --------------------------------------------------------

  /// Retorna null se deu certo, ou a mensagem de erro.
  Future<String?> pair(LanPeer p, String code) async {
    if (p.salt == null) return 'O outro celular não está com o pareamento aberto.';
    final codeKey =
        await Crypto.deriveKey(Crypto.normalizeCode(code), base64Decode(p.salt!));
    final sealed = await Crypto.sealJson(codeKey, {'id': Device.id, 'name': Device.name});
    final r = await _request(p.ip, '/pair',
        body: {'c': sealed}, timeout: const Duration(seconds: 90));
    switch (r.status) {
      case 200:
        final key = await Crypto.open(codeKey, r.json!['c'] as String);
        peers[p.id] = SavedPeer(p.id, p.name, p.ip, base64Encode(key))
          ..online = true;
        await _persist();
        notifyListeners();
        await syncOne(peers[p.id]!);
        return null;
      case 403:
        return 'Código incorreto ou acesso negado no outro celular.';
      case 429:
        return 'Muitas tentativas. Abra o pareamento de novo no outro celular.';
      default:
        return 'Não consegui falar com o outro celular.';
    }
  }

  // ---- sincronização -----------------------------------------------------

  Future<bool> syncOne(SavedPeer p) async {
    final key = SecretKey(base64Decode(p.key));
    final now = DateTime.now().millisecondsSinceEpoch;
    final sealed = await Crypto.sealJson(
        key, {'ts': now, 'snapshot': store.exportSnapshot()},
        aad: utf8.encode(Device.id));
    final r = await _request(p.ip, '/sync', body: {'id': Device.id, 'c': sealed});
    if (r.status == 403) {
      status = '“${p.name}” recusou: o acesso foi revogado ou o relógio está errado.';
      p.online = false;
      return false;
    }
    if (r.status != 200 || r.json == null) {
      p.online = false;
      return false;
    }
    try {
      final msg = await Crypto.openJson(key, r.json!['c'] as String,
          aad: utf8.encode('resp:${Device.id}'));
      if ((DateTime.now().millisecondsSinceEpoch - (msg['ts'] as int)).abs() >
          5 * 60 * 1000) {
        return false;
      }
      await store.mergeSnapshot(Map<String, dynamic>.from(msg['snapshot'] as Map));
    } catch (_) {
      return false;
    }
    p.online = true;
    p.lastSync = DateTime.now().millisecondsSinceEpoch;
    return true;
  }

  /// Sincroniza com todos os pareados; os que sumiram são procurados de novo
  /// (o IP pode ter mudado). Quem estiver sem conexão entra na próxima rodada.
  Future<void> syncAll() async {
    if (busy || peers.isEmpty) return;
    busy = true;
    notifyListeners();
    try {
      for (final p in peers.values) {
        await syncOne(p);
      }
      final offline = peers.values.where((p) => !p.online).toList();
      if (offline.isNotEmpty &&
          DateTime.now().difference(_lastScan) > const Duration(minutes: 2)) {
        final found = {for (final f in await scan()) f.id: f};
        for (final p in offline) {
          final f = found[p.id];
          if (f != null) {
            p.ip = f.ip;
            await syncOne(p);
          }
        }
      }
      status = null;
      await _persist();
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _debounce?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    store.removeListener(_onStoreChanged);
    super.dispose();
  }
}

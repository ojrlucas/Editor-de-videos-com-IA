import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import '../services/task_store.dart';
import 'crypto.dart';
import 'device.dart';

/// Versão online: o servidor só guarda um bloco cifrado; quem tem a frase
/// secreta decifra. A frase nunca sai do aparelho.
class CloudSync extends ChangeNotifier with WidgetsBindingObserver {
  static const _salt = 'prazo-online-v1';
  final TaskStore store;
  CloudSync(this.store);

  String? url;
  String? _room;
  SecretKey? _key;
  bool autoSync = true;
  bool busy = false;
  String? status;
  int lastSync = 0;
  Timer? _timer;
  Timer? _debounce;

  bool get configured => url != null && _key != null;

  Future<void> start() async {
    final p = Device.prefs;
    url = p.getString('cloud_url_v1');
    final k = p.getString('cloud_key_v1');
    if (k != null) {
      _key = SecretKey(base64Decode(k));
      _room = p.getString('cloud_room_v1');
    }
    autoSync = p.getBool('cloud_auto_v1') ?? true;
    lastSync = p.getInt('cloud_last_v1') ?? 0;
    WidgetsBinding.instance.addObserver(this);
    store.addListener(_onStoreChanged);
    _timer = Timer.periodic(const Duration(minutes: 1), (_) {
      if (autoSync) sync();
    });
    if (autoSync && configured) sync();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed && autoSync && configured) sync();
  }

  void _onStoreChanged() {
    if (busy || !autoSync || !configured) return;
    _debounce?.cancel();
    _debounce = Timer(const Duration(seconds: 4), sync);
  }

  Future<void> setAuto(bool v) async {
    autoSync = v;
    await Device.prefs.setBool('cloud_auto_v1', v);
    notifyListeners();
  }

  /// Retorna null se ok, ou a mensagem de erro.
  Future<String?> connect(String serverUrl, String phrase) async {
    final u = serverUrl.trim().replaceAll(RegExp(r'/+$'), '');
    if (!u.startsWith('https://')) {
      return 'O endereço precisa começar com https:// (conexão segura).';
    }
    if (phrase.trim().length < 12) {
      return 'A frase secreta precisa ter pelo menos 12 caracteres.';
    }
    final key = await Crypto.deriveKey(phrase.trim(), utf8.encode(_salt),
        iterations: 200000);
    final bytes = await key.extractBytes();
    final room = await Crypto.sha256Hex([...utf8.encode('room:'), ...bytes]);
    url = u;
    _key = key;
    _room = room;
    await Device.prefs.setString('cloud_url_v1', u);
    await Device.prefs.setString('cloud_key_v1', base64Encode(bytes));
    await Device.prefs.setString('cloud_room_v1', room);
    notifyListeners();
    return sync();
  }

  Future<void> disconnect() async {
    url = null;
    _key = null;
    _room = null;
    for (final k in ['cloud_url_v1', 'cloud_key_v1', 'cloud_room_v1']) {
      await Device.prefs.remove(k);
    }
    notifyListeners();
  }

  Future<(int, Map<String, dynamic>?)> _http(String method, Map<String, dynamic>? body) async {
    final c = HttpClient()..connectionTimeout = const Duration(seconds: 15);
    try {
      final req = await c.openUrl(method, Uri.parse('$url/v1/rooms/$_room'));
      if (body != null) {
        req.headers.contentType = ContentType.json;
        req.add(utf8.encode(jsonEncode(body)));
      }
      final res = await req.close().timeout(const Duration(seconds: 30));
      final text = await utf8.decodeStream(res);
      Map<String, dynamic>? j;
      try {
        j = jsonDecode(text) as Map<String, dynamic>;
      } catch (_) {}
      return (res.statusCode, j);
    } catch (_) {
      return (0, null);
    } finally {
      c.close(force: true);
    }
  }

  /// Baixa, mescla, e envia de volta o resultado. Retorna null se ok.
  Future<String?> sync() async {
    if (!configured) return 'Não conectado.';
    if (busy) return null;
    busy = true;
    notifyListeners();
    try {
      for (var attempt = 0; attempt < 3; attempt++) {
        final (st, j) = await _http('GET', null);
        var version = 0;
        if (st == 200 && j != null) {
          version = j['version'] as int;
          final snap = await Crypto.openJson(_key!, j['blob'] as String,
              aad: utf8.encode(_room!));
          await store.mergeSnapshot(snap);
        } else if (st != 404) {
          status = st == 0
              ? 'Sem conexão com o servidor. Tentarei de novo.'
              : 'Servidor respondeu $st.';
          return status;
        }
        final blob = await Crypto.sealJson(_key!, store.exportSnapshot(),
            aad: utf8.encode(_room!));
        final (ps, _) = await _http('PUT', {'base': version, 'blob': blob});
        if (ps == 200) {
          lastSync = DateTime.now().millisecondsSinceEpoch;
          await Device.prefs.setInt('cloud_last_v1', lastSync);
          status = null;
          return null;
        }
        if (ps != 409) {
          status = ps == 0 ? 'Sem conexão com o servidor.' : 'Servidor respondeu $ps.';
          return status;
        }
        // 409: outro aparelho enviou antes; baixa de novo e tenta mesclar.
      }
      status = 'Muitos conflitos seguidos. Tente de novo.';
      return status;
    } catch (_) {
      status = 'Erro ao sincronizar (frase secreta diferente da usada nos outros aparelhos?).';
      return status;
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

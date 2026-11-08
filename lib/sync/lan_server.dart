import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';

import '../services/task_store.dart';
import 'crypto.dart';
import 'device.dart';

class PairedDevice {
  final String id;
  String name;
  final String key; // base64 da chave de 256 bits
  final int pairedAt;
  int lastSync;
  PairedDevice(this.id, this.name, this.key, this.pairedAt, [this.lastSync = 0]);

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'key': key,
        'pairedAt': pairedAt,
        'lastSync': lastSync
      };
  factory PairedDevice.fromJson(Map<String, dynamic> j) => PairedDevice(
      j['id'] as String,
      j['name'] as String,
      j['key'] as String,
      j['pairedAt'] as int,
      j['lastSync'] as int? ?? 0);
}

/// Servidor da versão normal: só responde na rede local, só com mensagens
/// criptografadas, só para aparelhos pareados com um código de uso único.
class LanServer extends ChangeNotifier {
  static const port = 48765;
  static const _maxBody = 4 * 1024 * 1024;
  static const _maxSkewMs = 5 * 60 * 1000;
  static const _pairWindow = Duration(minutes: 5);
  static const _maxAttempts = 5;

  final TaskStore store;
  LanServer(this.store);

  HttpServer? _server;
  final Map<String, PairedDevice> _devices = {};
  bool running = false;
  String? error;

  // Pareamento aberto.
  String? pairingCode;
  DateTime? pairingUntil;
  Uint8List? _salt;
  SecretKey? _codeKey;
  int _attempts = 0;

  /// Pergunta ao dono se aceita o novo aparelho (a UI preenche isto).
  Future<bool> Function(String deviceName)? onPairRequest;

  final Map<String, int> _seen = {}; // nonce -> instante, contra repetição

  List<PairedDevice> get devices => _devices.values.toList();
  bool get pairingOpen =>
      pairingCode != null && DateTime.now().isBefore(pairingUntil!);

  Future<void> start() async {
    final raw = Device.prefs.getString('lan_devices_v1');
    if (raw != null) {
      for (final e in jsonDecode(raw) as List) {
        final d = PairedDevice.fromJson(Map<String, dynamic>.from(e as Map));
        _devices[d.id] = d;
      }
    }
    try {
      _server = await HttpServer.bind(InternetAddress.anyIPv4, port);
      running = true;
      _server!.listen(_handle, onError: (_) {});
    } on SocketException catch (e) {
      error = e.message;
    }
    notifyListeners();
  }

  Future<void> _persist() => Device.prefs.setString(
      'lan_devices_v1', jsonEncode(_devices.values.map((d) => d.toJson()).toList()));

  Future<void> openPairing() async {
    pairingCode = Crypto.newCode();
    pairingUntil = DateTime.now().add(_pairWindow);
    _attempts = 0;
    _salt = Crypto.randomBytes(16);
    _codeKey = await Crypto.deriveKey(pairingCode!, _salt!);
    notifyListeners();
    Timer(_pairWindow + const Duration(seconds: 1), () {
      if (!pairingOpen) closePairing();
    });
  }

  void closePairing() {
    pairingCode = null;
    pairingUntil = null;
    _codeKey = null;
    _salt = null;
    notifyListeners();
  }

  Future<void> revoke(String id) async {
    _devices.remove(id);
    await _persist();
    notifyListeners();
  }

  // ---- HTTP --------------------------------------------------------------

  Future<void> _handle(HttpRequest req) async {
    try {
      final path = req.uri.path;
      if (req.method == 'GET' && path == '/hello') {
        return _json(req, 200, {
          'app': 'prazo',
          'id': Device.id,
          'name': Device.name,
          'pairing': pairingOpen,
          if (pairingOpen) 'salt': base64Encode(_salt!),
        });
      }
      if (req.method != 'POST') return _json(req, 405, {});
      final body = await _readJson(req);
      if (body == null) return _json(req, 400, {});
      if (path == '/pair') return await _pair(req, body);
      if (path == '/sync') return await _sync(req, body);
      return _json(req, 404, {});
    } catch (_) {
      try {
        _json(req, 500, {});
      } catch (_) {}
    }
  }

  Future<Map<String, dynamic>?> _readJson(HttpRequest req) async {
    var size = 0;
    final chunks = <int>[];
    await for (final c in req) {
      size += c.length;
      if (size > _maxBody) return null;
      chunks.addAll(c);
    }
    try {
      return jsonDecode(utf8.decode(chunks)) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  void _json(HttpRequest req, int status, Object body) {
    req.response
      ..statusCode = status
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(body));
    req.response.close();
  }

  Future<void> _pair(HttpRequest req, Map<String, dynamic> body) async {
    if (!pairingOpen) return _json(req, 403, {'e': 'closed'});
    if (_attempts >= _maxAttempts) {
      closePairing();
      return _json(req, 429, {'e': 'locked'});
    }
    Map<String, dynamic> hello;
    try {
      hello = await Crypto.openJson(_codeKey!, body['c'] as String);
    } catch (_) {
      _attempts++;
      if (_attempts >= _maxAttempts) closePairing();
      return _json(req, 403, {'e': 'bad-code'});
    }
    final id = hello['id'] as String;
    final name = hello['name'] as String;
    final ok = await (onPairRequest?.call(name) ?? Future.value(false));
    if (!ok) return _json(req, 403, {'e': 'denied'});

    final key = Crypto.randomBytes(32);
    final codeKey = _codeKey!;
    _devices[id] = PairedDevice(id, name, base64Encode(key), _nowMs());
    await _persist();
    final sealed = await Crypto.seal(codeKey, key);
    closePairing(); // código de uso único
    _json(req, 200, {'c': sealed});
  }

  Future<void> _sync(HttpRequest req, Map<String, dynamic> body) async {
    final id = body['id'] as String?;
    final dev = id == null ? null : _devices[id];
    if (dev == null) return _json(req, 403, {'e': 'unknown'});
    final key = SecretKey(base64Decode(dev.key));

    final sealed = body['c'] as String;
    final nonce = sealed.substring(0, 16);
    final now = DateTime.now().millisecondsSinceEpoch;
    _seen.removeWhere((_, t) => now - t > 2 * _maxSkewMs);
    if (_seen.containsKey(nonce)) return _json(req, 403, {'e': 'replay'});

    Map<String, dynamic> msg;
    try {
      msg = await Crypto.openJson(key, sealed, aad: utf8.encode(id!));
    } catch (_) {
      return _json(req, 403, {'e': 'bad-mac'});
    }
    if ((now - (msg['ts'] as int)).abs() > _maxSkewMs) {
      return _json(req, 403, {'e': 'clock'});
    }
    _seen[nonce] = now;

    await store.mergeSnapshot(Map<String, dynamic>.from(msg['snapshot'] as Map));
    dev.lastSync = now;
    await _persist();
    notifyListeners();

    final reply = await Crypto.sealJson(
        key, {'ts': now, 'snapshot': store.exportSnapshot()},
        aad: utf8.encode('resp:$id'));
    _json(req, 200, {'c': reply});
  }

  static int _nowMs() => DateTime.now().millisecondsSinceEpoch;
}

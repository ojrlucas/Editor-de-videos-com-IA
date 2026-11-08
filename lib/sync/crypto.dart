import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// AES-256-GCM (autenticado) + PBKDF2. Nada trafega em texto aberto.
class Crypto {
  static final _aes = AesGcm.with256bits();
  static final _rng = Random.secure();

  /// Sem caracteres ambíguos (0/O, 1/I). 10 caracteres = 50 bits.
  static const _alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

  static Uint8List randomBytes(int n) =>
      Uint8List.fromList(List.generate(n, (_) => _rng.nextInt(256)));

  static String newCode() =>
      List.generate(10, (_) => _alphabet[_rng.nextInt(_alphabet.length)]).join();

  static String normalizeCode(String s) =>
      s.toUpperCase().replaceAll(RegExp(r'[^A-Z0-9]'), '');

  static Future<SecretKey> deriveKey(String secret, List<int> salt,
      {int iterations = 100000}) {
    final kdf = Pbkdf2(
        macAlgorithm: Hmac.sha256(), iterations: iterations, bits: 256);
    return kdf.deriveKeyFromPassword(password: secret, nonce: salt);
  }

  static Future<String> seal(SecretKey key, List<int> plain,
      {List<int> aad = const []}) async {
    final box = await _aes.encrypt(plain, secretKey: key, aad: aad);
    return base64Encode(box.concatenation());
  }

  static Future<Uint8List> open(SecretKey key, String b64,
      {List<int> aad = const []}) async {
    final box = SecretBox.fromConcatenation(base64Decode(b64),
        nonceLength: 12, macLength: 16);
    return Uint8List.fromList(await _aes.decrypt(box, secretKey: key, aad: aad));
  }

  static Future<String> sealJson(SecretKey key, Object json,
          {List<int> aad = const []}) =>
      seal(key, utf8.encode(jsonEncode(json)), aad: aad);

  static Future<Map<String, dynamic>> openJson(SecretKey key, String b64,
          {List<int> aad = const []}) async =>
      jsonDecode(utf8.decode(await open(key, b64, aad: aad)))
          as Map<String, dynamic>;

  static Future<String> sha256Hex(List<int> data) async {
    final h = await Sha256().hash(data);
    return h.bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}

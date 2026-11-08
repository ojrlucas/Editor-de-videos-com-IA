import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';

class AuthService {
  static final _auth = LocalAuthentication();

  /// Pede a digital (ou o bloqueio de tela do aparelho como alternativa).
  /// Retorna false se o usuário cancelar ou errar; true se o aparelho não tem
  /// nenhum bloqueio configurado (não há como autenticar).
  static Future<bool> confirm(String reason) async {
    try {
      if (!await _auth.isDeviceSupported()) return true;
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(stickyAuth: true),
      );
    } on PlatformException {
      return false;
    }
  }
}

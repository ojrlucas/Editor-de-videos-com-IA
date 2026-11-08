/// Qual APK é este. Definido na compilação: --dart-define=EDITION=normal|dev|online
enum Edition { normal, dev, online }

final Edition kEdition = switch (const String.fromEnvironment('EDITION')) {
  'dev' => Edition.dev,
  'online' => Edition.online,
  _ => Edition.normal,
};

String get appTitle => switch (kEdition) {
      Edition.normal => 'Prazo',
      Edition.dev => 'Prazo Dev',
      Edition.online => 'Prazo Online',
    };

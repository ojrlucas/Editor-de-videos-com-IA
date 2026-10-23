#!/usr/bin/env bash
# Gera as pastas android/ e ios/, aplica os ajustes do Prazo e baixa as dependências.
set -euo pipefail
cd "$(dirname "$0")/.."
flutter create --project-name prazo --org br.com.prazo --platforms android,ios .
rm -f test/widget_test.dart
python3 tool/patch_android.py
flutter pub get
echo "Pronto. Rode: flutter run   |   flutter build apk --release"

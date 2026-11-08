#!/usr/bin/env python3
"""Ajusta o projeto Android gerado por `flutter create` para o Prazo:
permissões, receivers de alarme/boot, tela cheia sobre o bloqueio e desugaring."""
import pathlib
import re
import sys

edition = sys.argv[sys.argv.index("--edition") + 1] if "--edition" in sys.argv else "normal"
labels = {"normal": "Prazo", "dev": "Prazo Dev", "online": "Prazo Online"}

root = pathlib.Path(__file__).resolve().parent.parent / "android" / "app"
manifest = root / "src" / "main" / "AndroidManifest.xml"
if not manifest.exists():
    sys.exit("android/ não encontrado. Rode `flutter create` antes.")

MARK = "<!-- prazo-patched -->"
m = manifest.read_text()
if MARK not in m:
    perms = "\n".join(
        f'    <uses-permission android:name="android.permission.{p}"/>'
        for p in [
            "POST_NOTIFICATIONS",
            "SCHEDULE_EXACT_ALARM",
            "USE_FULL_SCREEN_INTENT",
            "RECEIVE_BOOT_COMPLETED",
            "VIBRATE",
            "WAKE_LOCK",
            "USE_BIOMETRIC",
            "INTERNET",
            "ACCESS_NETWORK_STATE",
        ]
    )
    receivers = """
        <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver"/>
        <receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED"/>
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED"/>
                <action android:name="android.intent.action.QUICKBOOT_POWERON"/>
                <action android:name="com.htc.intent.action.QUICKBOOT_POWERON"/>
            </intent-filter>
        </receiver>
"""
    m = m.replace("<application", f"{MARK}\n{perms}\n    <application", 1)
    m = re.sub(r'android:label="[^"]*"', f'android:label="{labels[edition]}"', m, count=1)
    m = m.replace(
        "<activity",
        '<activity android:showWhenLocked="true" android:turnScreenOn="true"',
        1,
    )
    if edition != "online":
        # Na rede local o app fala HTTP simples, mas com o conteúdo cifrado (AES-256).
        # A versão online só aceita https://.
        m = re.sub(r"<application(\s)", r'<application android:usesCleartextTraffic="true"\1', m, count=1)
    m = m.replace("</application>", receivers + "    </application>", 1)
    manifest.write_text(m)
    print("AndroidManifest.xml ajustado")

# Desugaring exigido por flutter_local_notifications.
for name, kts in (("build.gradle.kts", True), ("build.gradle", False)):
    g = root / name
    if not g.exists():
        continue
    t = g.read_text()
    if "coreLibraryDesugaring" in t:
        break
    if kts:
        t = re.sub(r"compileOptions\s*\{",
                   "compileOptions {\n        isCoreLibraryDesugaringEnabled = true", t, count=1)
        t += '\ndependencies {\n    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")\n}\n'
    else:
        t = re.sub(r"compileOptions\s*\{",
                   "compileOptions {\n        coreLibraryDesugaringEnabled true", t, count=1)
        t += "\ndependencies {\n    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'\n}\n"
    g.write_text(t)
    print(f"{name} ajustado")
    break

# local_auth exige FlutterFragmentActivity.
for kt in (root / "src" / "main").rglob("MainActivity.kt"):
    t = kt.read_text()
    if "FlutterFragmentActivity" not in t:
        t = t.replace("io.flutter.embedding.android.FlutterActivity",
                      "io.flutter.embedding.android.FlutterFragmentActivity")
        t = t.replace(": FlutterActivity()", ": FlutterFragmentActivity()")
        kt.write_text(t)
        print("MainActivity ajustada")

# Cada edição tem seu próprio applicationId, para poderem ficar instaladas juntas.
for name in ("build.gradle.kts", "build.gradle"):
    g = root / name
    if g.exists():
        t = g.read_text()
        t = re.sub(r'applicationId\s*=?\s*"[^"]*"', f'applicationId = "br.com.prazo.{edition}"', t, count=1)
        g.write_text(t)
        print(f"applicationId = br.com.prazo.{edition}")
        break

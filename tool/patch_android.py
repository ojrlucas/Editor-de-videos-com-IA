#!/usr/bin/env python3
"""Ajusta o projeto Android gerado por `flutter create` para o Prazo:
permissões, receivers de alarme/boot, tela cheia sobre o bloqueio e desugaring."""
import pathlib
import re
import sys

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
    m = re.sub(r'android:label="[^"]*"', 'android:label="Prazo"', m, count=1)
    m = m.replace(
        "<activity",
        '<activity android:showWhenLocked="true" android:turnScreenOn="true"',
        1,
    )
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

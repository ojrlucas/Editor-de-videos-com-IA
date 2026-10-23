import 'dart:typed_data';

import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:intl/intl.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import '../models/task.dart';
import '../utils.dart';

/// Ids de notificação: `taskId * 10 + slot`.
/// slot 0 = alerta de ligação, 1..8 = lembretes, 9 = adiamento (soneca).
/// taskId 0 é reservado para a ligação de teste.
class NotificationService {
  NotificationService._();
  static final instance = NotificationService._();

  static const actionAnswer = 'answer';
  static const actionDone = 'done';
  static const actionSnooze = 'snooze';
  static const snoozeMinutes = 10;

  final _plugin = FlutterLocalNotificationsPlugin();

  AndroidFlutterLocalNotificationsPlugin? get _android =>
      _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();

  int _id(int taskId, int slot) => taskId * 10 + slot;

  Future<void> init(void Function(NotificationResponse) onResponse) async {
    tzdata.initializeTimeZones();
    try {
      tz.setLocalLocation(
          tz.getLocation(await FlutterTimezone.getLocalTimezone()));
    } catch (_) {
      tz.setLocalLocation(tz.getLocation('America/Sao_Paulo'));
    }

    await _plugin.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
      onDidReceiveNotificationResponse: onResponse,
    );
  }

  /// Resposta que abriu o app (toque na notificação / tela cheia) com o app fechado.
  Future<NotificationResponse?> launchResponse() async {
    final d = await _plugin.getNotificationAppLaunchDetails();
    return (d?.didNotificationLaunchApp ?? false) ? d!.notificationResponse : null;
  }

  Future<void> requestPermissions() async {
    final a = _android;
    if (a != null) {
      await a.requestNotificationsPermission();
      await a.requestExactAlarmsPermission();
      await a.requestFullScreenIntentPermission();
    }
    await _plugin
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(alert: true, badge: true, sound: true);
  }

  // ---- detalhes ----------------------------------------------------------

  NotificationDetails get _reminderDetails => const NotificationDetails(
        android: AndroidNotificationDetails(
          'reminders',
          'Lembretes',
          channelDescription: 'Lembretes de prazo das tarefas',
          importance: Importance.high,
          priority: Priority.high,
          category: AndroidNotificationCategory.reminder,
        ),
        iOS: DarwinNotificationDetails(
          presentAlert: true,
          presentSound: true,
          interruptionLevel: InterruptionLevel.timeSensitive,
        ),
      );

  NotificationDetails get _callDetails => NotificationDetails(
        android: AndroidNotificationDetails(
          'calls',
          'Ligações de tarefa',
          channelDescription:
              'Alerta estilo ligação, em tela cheia, antes da tarefa vencer',
          importance: Importance.max,
          priority: Priority.max,
          category: AndroidNotificationCategory.call,
          fullScreenIntent: true,
          ongoing: true,
          autoCancel: false,
          playSound: true,
          audioAttributesUsage: AudioAttributesUsage.alarm,
          enableVibration: true,
          vibrationPattern: Int64List.fromList(
              [0, 1200, 800, 1200, 800, 1200, 800, 1200, 800, 1200]),
          // FLAG_INSISTENT: repete o som até o usuário agir ou o tempo acabar.
          additionalFlags: Int32List.fromList(<int>[4]),
          timeoutAfter: 60000,
          visibility: NotificationVisibility.public,
          actions: const [
            AndroidNotificationAction(actionAnswer, 'Atender',
                showsUserInterface: true, cancelNotification: true),
            AndroidNotificationAction(actionDone, 'Concluir',
                showsUserInterface: true, cancelNotification: true),
            AndroidNotificationAction(actionSnooze, 'Adiar 10 min',
                showsUserInterface: true, cancelNotification: true),
          ],
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentSound: true,
          interruptionLevel: InterruptionLevel.timeSensitive,
        ),
      );

  // ---- agendamento -------------------------------------------------------

  Future<void> _zoned(int id, String title, String body, DateTime when,
      NotificationDetails details, String payload) async {
    final at = tz.TZDateTime.from(when, tz.local);
    try {
      await _plugin.zonedSchedule(id, title, body, at, details,
          androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
          uiLocalNotificationDateInterpretation:
              UILocalNotificationDateInterpretation.absoluteTime,
          payload: payload);
    } on PlatformException {
      // Sem permissão de alarme exato: usa agendamento aproximado.
      await _plugin.zonedSchedule(id, title, body, at, details,
          androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
          uiLocalNotificationDateInterpretation:
              UILocalNotificationDateInterpretation.absoluteTime,
          payload: payload);
    }
  }

  Future<void> cancelTask(int taskId) async {
    for (var s = 0; s < 10; s++) {
      await _plugin.cancel(_id(taskId, s));
    }
  }

  Future<void> cancel(int notificationId) => _plugin.cancel(notificationId);

  Future<void> scheduleTask(Task t) async {
    await cancelTask(t.id);
    if (t.done) return;
    final now = DateTime.now();

    final reminders = [...t.reminders]..sort();
    for (var i = 0; i < reminders.length && i < 8; i++) {
      final m = reminders[i];
      final when = t.due.subtract(Duration(minutes: m));
      if (when.isAfter(now)) {
        await _zoned(
          _id(t.id, i + 1),
          t.title,
          m == 0
              ? 'O prazo é agora (${DateFormat.Hm().format(t.due)}).'
              : 'Vence em ${durationText(Duration(minutes: m))} '
                  '(às ${DateFormat.Hm().format(t.due)}).',
          when,
          _reminderDetails,
          'rem:${t.id}',
        );
      }
    }

    if (t.callAlert) {
      final when = t.due.subtract(Duration(minutes: t.callMinutes));
      if (when.isAfter(now)) await _scheduleCall(t, when);
    }
  }

  Future<void> _scheduleCall(Task t, DateTime when, {int slot = 0}) =>
      _zoned(
        _id(t.id, slot),
        '📞 ${t.title}',
        'Vence às ${DateFormat.Hm().format(t.due)} — toque para atender',
        when,
        _callDetails,
        'call:${t.id}',
      );

  /// Faz a "ligação" tocar de novo daqui a [minutes].
  Future<void> snoozeCall(Task t, int minutes) =>
      _scheduleCall(t, DateTime.now().add(Duration(minutes: minutes)), slot: 9);

  Future<void> scheduleTestCall({int seconds = 10}) => _zoned(
        _id(0, 0),
        '📞 Tarefa de teste',
        'Assim vai ser a ligação antes de uma tarefa vencer',
        DateTime.now().add(Duration(seconds: seconds)),
        _callDetails,
        'test:0',
      );
}

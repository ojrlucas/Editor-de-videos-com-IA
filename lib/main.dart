import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'models/task.dart';
import 'screens/call_screen.dart';
import 'screens/home_screen.dart';
import 'screens/task_editor.dart';
import 'services/notification_service.dart';
import 'services/task_store.dart';

final navigatorKey = GlobalKey<NavigatorState>();
late final TaskStore _store;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('pt_BR');
  await NotificationService.instance.init(_onNotification);
  _store = TaskStore();
  await _store.load();

  final launch = await NotificationService.instance.launchResponse();
  runApp(ChangeNotifierProvider.value(value: _store, child: const PrazoApp()));
  if (launch != null) {
    WidgetsBinding.instance.addPostFrameCallback((_) => _onNotification(launch));
  }
}

/// Trata toques e botões de ações das notificações.
void _onNotification(NotificationResponse r) {
  final parts = (r.payload ?? '').split(':');
  if (parts.length != 2) return;
  final kind = parts[0];
  final id = int.tryParse(parts[1]) ?? -1;
  final nav = navigatorKey.currentState;
  if (r.id != null) NotificationService.instance.cancel(r.id!);

  final task = kind == 'test'
      ? Task(
          id: 0,
          title: 'Tarefa de teste',
          due: DateTime.now().add(const Duration(minutes: 10)))
      : _store.byId(id);
  if (task == null || nav == null) return;

  switch (r.actionId) {
    case NotificationService.actionDone:
      if (kind != 'test') _store.setDone(task, true);
    case NotificationService.actionSnooze:
      if (kind != 'test') {
        _store.snoozeCall(task, NotificationService.snoozeMinutes);
      }
    default:
      if (kind == 'call' || kind == 'test') {
        nav.push(MaterialPageRoute(
            fullscreenDialog: true, builder: (_) => CallScreen(task: task)));
      } else {
        nav.push(MaterialPageRoute(builder: (_) => TaskEditor(task: task)));
      }
  }
}

class PrazoApp extends StatelessWidget {
  const PrazoApp({super.key});

  @override
  Widget build(BuildContext context) {
    ThemeData theme(Brightness b) => ThemeData(
          useMaterial3: true,
          colorSchemeSeed: const Color(0xFF4F46E5),
          brightness: b,
        );
    return MaterialApp(
      title: 'Prazo',
      navigatorKey: navigatorKey,
      debugShowCheckedModeBanner: false,
      theme: theme(Brightness.light),
      darkTheme: theme(Brightness.dark),
      locale: const Locale('pt', 'BR'),
      supportedLocales: const [Locale('pt', 'BR')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: const HomeScreen(),
    );
  }
}

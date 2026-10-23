import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../models/task.dart';
import '../services/notification_service.dart';
import '../services/task_store.dart';
import '../utils.dart';
import 'task_editor.dart';

/// Tela de "ligação recebida" mostrada quando o alerta dispara.
class CallScreen extends StatefulWidget {
  final Task task;
  const CallScreen({super.key, required this.task});

  @override
  State<CallScreen> createState() => _CallScreenState();
}

class _CallScreenState extends State<CallScreen> {
  Timer? _tick;
  Timer? _buzz;

  @override
  void initState() {
    super.initState();
    _tick = Timer.periodic(const Duration(seconds: 1), (_) => setState(() {}));
    _buzz = Timer.periodic(
        const Duration(milliseconds: 1500), (_) => HapticFeedback.heavyImpact());
  }

  @override
  void dispose() {
    _tick?.cancel();
    _buzz?.cancel();
    super.dispose();
  }

  bool get _isTest => widget.task.id == 0;

  void _close() => Navigator.of(context).pop();

  @override
  Widget build(BuildContext context) {
    final t = widget.task;
    final store = context.read<TaskStore>();
    return Scaffold(
      backgroundColor: const Color(0xFF111827),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 48, 24, 40),
          child: Column(
            children: [
              const Text('TAREFA CHAMANDO…',
                  style: TextStyle(color: Colors.white54, letterSpacing: 3)),
              const SizedBox(height: 40),
              const CircleAvatar(
                radius: 56,
                backgroundColor: Color(0xFF4F46E5),
                child: Icon(Icons.alarm, size: 56, color: Colors.white),
              ),
              const SizedBox(height: 28),
              Text(t.title,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.w600)),
              const SizedBox(height: 12),
              Text(relativeDue(t.due),
                  style: const TextStyle(color: Colors.amberAccent, fontSize: 18)),
              const SizedBox(height: 6),
              Text(fullDue(t.due),
                  style: const TextStyle(color: Colors.white54)),
              if (t.notes.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text(t.notes,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white70)),
              ],
              const Spacer(),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _CallButton(
                    color: Colors.orange,
                    icon: Icons.snooze,
                    label: 'Adiar ${NotificationService.snoozeMinutes} min',
                    onTap: () {
                      if (!_isTest) {
                        store.snoozeCall(t, NotificationService.snoozeMinutes);
                      }
                      _close();
                    },
                  ),
                  _CallButton(
                    color: Colors.green,
                    icon: Icons.check,
                    label: 'Concluir',
                    onTap: () {
                      if (!_isTest) store.setDone(t, true);
                      _close();
                    },
                  ),
                  _CallButton(
                    color: Colors.blue,
                    icon: Icons.call,
                    label: 'Atender',
                    onTap: () {
                      final nav = Navigator.of(context);
                      nav.pop();
                      if (!_isTest) {
                        nav.push(MaterialPageRoute(
                            builder: (_) => TaskEditor(task: t)));
                      }
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CallButton extends StatelessWidget {
  final Color color;
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _CallButton(
      {required this.color,
      required this.icon,
      required this.label,
      required this.onTap});

  @override
  Widget build(BuildContext context) => Column(
        children: [
          FloatingActionButton.large(
            heroTag: label,
            backgroundColor: color,
            foregroundColor: Colors.white,
            shape: const CircleBorder(),
            onPressed: onTap,
            child: Icon(icon, size: 36),
          ),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(color: Colors.white70)),
        ],
      );
}

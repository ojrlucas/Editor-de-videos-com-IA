import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/account.dart';
import '../services/auth_service.dart';
import '../services/task_store.dart';

class AccountAvatar extends StatelessWidget {
  final Account account;
  final double radius;
  const AccountAvatar({super.key, required this.account, this.radius = 18});

  @override
  Widget build(BuildContext context) => CircleAvatar(
        radius: radius,
        backgroundColor: account.tint,
        child: Text(account.initial,
            style: TextStyle(color: Colors.white, fontSize: radius * 0.9)),
      );
}

/// Pede a digital e troca de conta. Se negar, continua logado na conta atual.
Future<bool> switchWithAuth(BuildContext context, Account target) async {
  final store = context.read<TaskStore>();
  final messenger = ScaffoldMessenger.of(context);
  final current = store.active;
  if (target.id == current.id) return true;
  final ok = await AuthService.confirm('Confirme para entrar em “${target.name}”');
  if (ok) {
    await store.switchAccount(target.id);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(
        SnackBar(content: Text('Conta: ${target.name}'), duration: const Duration(seconds: 2)));
    return true;
  }
  messenger.hideCurrentSnackBar();
  messenger.showSnackBar(SnackBar(
      content: Text('Autenticação negada. Continuando em “${current.name}”.')));
  return false;
}

/// Avatar da AppBar: deslizar para cima/baixo troca de conta; toque abre a lista.
class AccountButton extends StatelessWidget {
  const AccountButton({super.key});

  Future<void> _cycle(BuildContext context, int dir) async {
    final store = context.read<TaskStore>();
    final list = store.accounts;
    if (list.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Só há uma conta. Toque no avatar para adicionar outra.')));
      return;
    }
    final i = list.indexWhere((a) => a.id == store.active.id);
    final next = list[(i + dir + list.length) % list.length];
    await switchWithAuth(context, next);
  }

  @override
  Widget build(BuildContext context) {
    final active = context.watch<TaskStore>().active;
    return GestureDetector(
      onTap: () => showAccountSheet(context),
      onVerticalDragEnd: (d) {
        final v = d.primaryVelocity ?? 0;
        if (v.abs() < 200) return;
        _cycle(context, v < 0 ? 1 : -1); // para cima: próxima; para baixo: anterior
      },
      child: Padding(
        padding: const EdgeInsets.only(left: 12),
        child: Center(child: AccountAvatar(account: active)),
      ),
    );
  }
}

Future<String?> _askName(BuildContext context, String title, [String initial = '']) {
  final c = TextEditingController(text: initial);
  return showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: TextField(
          controller: c,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Nome')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        FilledButton(
            onPressed: () => Navigator.pop(ctx, c.text.trim()),
            child: const Text('OK')),
      ],
    ),
  );
}

void showAccountSheet(BuildContext context) {
  showModalBottomSheet(
    context: context,
    showDragHandle: true,
    builder: (sheet) => Consumer<TaskStore>(
      builder: (_, store, __) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            for (final a in store.accounts)
              ListTile(
                leading: AccountAvatar(account: a),
                title: Text(a.name),
                subtitle: a.id == store.active.id ? const Text('Conta atual') : null,
                trailing: PopupMenuButton<String>(
                  onSelected: (v) async {
                    if (v == 'rename') {
                      final n = await _askName(context, 'Renomear conta', a.name);
                      if (n != null && n.isNotEmpty) await store.renameAccount(a, n);
                    } else if (v == 'delete') {
                      final ok = await store.removeAccount(a);
                      if (!ok && context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                            content: Text(
                                'Não dá para remover a conta atual. Troque de conta antes.')));
                      }
                    }
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'rename', child: Text('Renomear')),
                    PopupMenuItem(value: 'delete', child: Text('Remover conta')),
                  ],
                ),
                onTap: () async {
                  final nav = Navigator.of(sheet);
                  if (await switchWithAuth(context, a)) nav.pop();
                },
              ),
            ListTile(
              leading: const CircleAvatar(child: Icon(Icons.add)),
              title: const Text('Adicionar conta'),
              onTap: () async {
                final n = await _askName(context, 'Nova conta');
                if (n != null && n.isNotEmpty) await store.addAccount(n);
              },
            ),
          ],
        ),
      ),
    ),
  );
}

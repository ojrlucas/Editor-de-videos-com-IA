import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../edition.dart';
import '../sync/cloud_sync.dart';
import '../sync/device.dart';
import '../sync/hub.dart';
import '../sync/lan_client.dart';
import '../sync/lan_server.dart';

String _ago(int ms) => ms == 0
    ? 'nunca'
    : DateFormat("d MMM · HH:mm", 'pt_BR')
        .format(DateTime.fromMillisecondsSinceEpoch(ms));

class SyncScreen extends StatelessWidget {
  const SyncScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Sincronização')),
        body: switch (kEdition) {
          Edition.normal => _NormalBody(lanServer!),
          Edition.dev => _DevBody(lanClient!),
          Edition.online => _OnlineBody(cloud!),
        },
      );
}

Future<void> _renameDevice(BuildContext context) async {
  final c = TextEditingController(text: Device.name);
  final n = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Nome deste celular'),
      content: TextField(controller: c, autofocus: true),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        FilledButton(onPressed: () => Navigator.pop(ctx, c.text), child: const Text('OK')),
      ],
    ),
  );
  if (n != null) await Device.rename(n);
}

// ---------------------------------------------------------------- normal

class _NormalBody extends StatefulWidget {
  final LanServer server;
  const _NormalBody(this.server);
  @override
  State<_NormalBody> createState() => _NormalBodyState();
}

class _NormalBodyState extends State<_NormalBody> {
  Timer? _t;

  @override
  void initState() {
    super.initState();
    _t = Timer.periodic(const Duration(seconds: 1), (_) => setState(() {}));
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.server;
    return ListenableBuilder(
      listenable: s,
      builder: (_, __) {
        final left = s.pairingUntil?.difference(DateTime.now());
        final code = s.pairingCode;
        return ListView(padding: const EdgeInsets.all(16), children: [
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(s.running ? Icons.wifi_tethering : Icons.wifi_off),
            title: Text(Device.name),
            subtitle: Text(s.running
                ? 'Visível só na sua rede wi-fi, para aparelhos pareados'
                : 'Não foi possível abrir a porta: ${s.error ?? ''}'),
            trailing: IconButton(
                icon: const Icon(Icons.edit), onPressed: () => _renameDevice(context)),
          ),
          const SizedBox(height: 8),
          if (code == null || (left?.isNegative ?? true))
            FilledButton.icon(
              icon: const Icon(Icons.add_link),
              label: const Text('Permitir um novo aparelho'),
              onPressed: s.openPairing,
            )
          else
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(children: [
                  const Text('Digite este código no celular Dev'),
                  const SizedBox(height: 12),
                  SelectableText(
                    '${code.substring(0, 5)}-${code.substring(5)}',
                    style: const TextStyle(
                        fontSize: 32, fontWeight: FontWeight.bold, letterSpacing: 3),
                  ),
                  const SizedBox(height: 8),
                  Text('Vale por ${left!.inMinutes}:${(left.inSeconds % 60).toString().padLeft(2, '0')} e funciona uma vez'),
                  TextButton(onPressed: s.closePairing, child: const Text('Cancelar')),
                ]),
              ),
            ),
          const SizedBox(height: 24),
          Text('Aparelhos com acesso', style: Theme.of(context).textTheme.titleSmall),
          if (s.devices.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Text('Nenhum ainda.'),
            ),
          for (final d in s.devices)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.phone_android),
              title: Text(d.name),
              subtitle: Text('Última sincronização: ${_ago(d.lastSync)}'),
              trailing: TextButton(
                onPressed: () => s.revoke(d.id),
                child: const Text('Revogar'),
              ),
            ),
          const SizedBox(height: 16),
          const Text(
            'Tudo trafega criptografado (AES-256). Um aparelho só entra com o '
            'código de uso único e com a sua confirmação. Mudanças feitas aqui '
            'chegam ao celular Dev quando ele estiver na mesma rede; se este '
            'celular ficar sem conexão, sincroniza assim que voltar.',
            style: TextStyle(fontSize: 12),
          ),
        ]);
      },
    );
  }
}

// ------------------------------------------------------------------- dev

class _DevBody extends StatefulWidget {
  final LanClient client;
  const _DevBody(this.client);
  @override
  State<_DevBody> createState() => _DevBodyState();
}

class _DevBodyState extends State<_DevBody> {
  List<LanPeer> _found = [];
  bool _scanning = false;
  final _ip = TextEditingController();

  Future<void> _scan() async {
    setState(() => _scanning = true);
    final r = await widget.client.scan();
    if (mounted) {
      setState(() {
        _found = r;
        _scanning = false;
      });
    }
  }

  Future<void> _pair(LanPeer p) async {
    final c = TextEditingController();
    final code = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Parear com ${p.name}'),
        content: TextField(
          controller: c,
          autofocus: true,
          textCapitalization: TextCapitalization.characters,
          decoration: const InputDecoration(
              labelText: 'Código mostrado no outro celular',
              hintText: 'XXXXX-XXXXX'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, c.text), child: const Text('Parear')),
        ],
      ),
    );
    if (code == null || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(const SnackBar(
        content: Text('Aguardando confirmação no outro celular…'),
        duration: Duration(seconds: 30)));
    final err = await widget.client.pair(p, code);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(content: Text(err ?? 'Pareado e sincronizado!')));
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.client;
    return ListenableBuilder(
      listenable: c,
      builder: (_, __) => ListView(padding: const EdgeInsets.all(16), children: [
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.developer_mode),
          title: Text(Device.name),
          subtitle: const Text('Celular Dev'),
          trailing: IconButton(
              icon: const Icon(Icons.edit), onPressed: () => _renameDevice(context)),
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Sincronizar automaticamente'),
          subtitle: const Text('A cada alteração e a cada 30 s com o app aberto'),
          value: c.autoSync,
          onChanged: c.setAuto,
        ),
        if (c.status != null)
          Text(c.status!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        const SizedBox(height: 8),
        Text('Celulares pareados', style: Theme.of(context).textTheme.titleSmall),
        if (c.peers.isEmpty)
          const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Text('Nenhum ainda.')),
        for (final p in c.peers.values)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(Icons.phone_android,
                color: p.online ? Colors.green : Theme.of(context).disabledColor),
            title: Text(p.name),
            subtitle: Text(p.online
                ? 'Conectado · ${_ago(p.lastSync)}'
                : 'Sem conexão · última vez ${_ago(p.lastSync)}\nAtualiza sozinho ao voltar'),
            isThreeLine: !p.online,
            trailing: PopupMenuButton<String>(
              onSelected: (v) => v == 'forget' ? c.forget(p.id) : c.syncAll(),
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'sync', child: Text('Sincronizar agora')),
                PopupMenuItem(value: 'forget', child: Text('Esquecer')),
              ],
            ),
          ),
        FilledButton.tonalIcon(
          icon: c.busy ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.sync),
          label: const Text('Sincronizar agora'),
          onPressed: c.busy ? null : c.syncAll,
        ),
        const Divider(height: 40),
        Text('Procurar celulares na rede', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        FilledButton.icon(
          icon: _scanning
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.radar),
          label: Text(_scanning ? 'Procurando…' : 'Procurar'),
          onPressed: _scanning ? null : _scan,
        ),
        for (final p in _found)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.smartphone),
            title: Text(p.name),
            subtitle: Text(c.peers.containsKey(p.id)
                ? 'Já pareado'
                : p.pairing
                    ? '${p.ip} · aguardando código'
                    : '${p.ip} · abra “Permitir um novo aparelho” nele'),
            trailing: c.peers.containsKey(p.id)
                ? null
                : TextButton(
                    onPressed: p.pairing ? () => _pair(p) : null,
                    child: const Text('Parear')),
          ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: TextField(
              controller: _ip,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                  labelText: 'Ou digite o IP do celular', hintText: '192.168.0.25'),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () async {
              final messenger = ScaffoldMessenger.of(context);
              final h = await c.helloPublic(_ip.text.trim());
              if (h == null) {
                messenger.showSnackBar(
                    const SnackBar(content: Text('Nada encontrado nesse IP.')));
              } else {
                setState(() => _found = [h, ..._found.where((e) => e.id != h.id)]);
              }
            },
          ),
        ]),
      ]),
    );
  }
}

// ---------------------------------------------------------------- online

class _OnlineBody extends StatefulWidget {
  final CloudSync cloud;
  const _OnlineBody(this.cloud);
  @override
  State<_OnlineBody> createState() => _OnlineBodyState();
}

class _OnlineBodyState extends State<_OnlineBody> {
  late final _url = TextEditingController(text: widget.cloud.url ?? 'https://');
  final _phrase = TextEditingController();
  String? _error;
  bool _working = false;

  Future<void> _connect() async {
    setState(() {
      _working = true;
      _error = null;
    });
    final e = await widget.cloud.connect(_url.text, _phrase.text);
    if (mounted) {
      setState(() {
        _working = false;
        _error = e;
      });
      if (e == null) _phrase.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.cloud;
    return ListenableBuilder(
      listenable: c,
      builder: (_, __) => ListView(padding: const EdgeInsets.all(16), children: [
        if (!c.configured) ...[
          const Text(
              'Use o mesmo endereço e a mesma frase secreta em todos os seus '
              'aparelhos. A frase nunca sai do celular: o servidor só guarda '
              'dados criptografados.'),
          const SizedBox(height: 16),
          TextField(
            controller: _url,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
                labelText: 'Endereço do servidor', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _phrase,
            obscureText: true,
            decoration: const InputDecoration(
                labelText: 'Frase secreta (mín. 12 caracteres)',
                border: OutlineInputBorder()),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          const SizedBox(height: 16),
          FilledButton(
              onPressed: _working ? null : _connect,
              child: Text(_working ? 'Conectando…' : 'Conectar')),
        ] else ...[
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.cloud_done),
            title: Text(c.url!),
            subtitle: Text('Última sincronização: ${_ago(c.lastSync)}'),
          ),
          if (c.status != null)
            Text(c.status!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Sincronizar automaticamente'),
            subtitle: const Text('A cada alteração e a cada minuto com o app aberto'),
            value: c.autoSync,
            onChanged: c.setAuto,
          ),
          FilledButton.icon(
            icon: const Icon(Icons.sync),
            label: Text(c.busy ? 'Sincronizando…' : 'Sincronizar agora'),
            onPressed: c.busy ? null : c.sync,
          ),
          TextButton(onPressed: c.disconnect, child: const Text('Desconectar')),
        ],
      ]),
    );
  }
}

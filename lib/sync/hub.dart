import '../edition.dart';
import '../services/task_store.dart';
import 'cloud_sync.dart';
import 'device.dart';
import 'lan_client.dart';
import 'lan_server.dart';

/// Só o serviço da edição atual é criado.
LanServer? lanServer;
LanClient? lanClient;
CloudSync? cloud;

Future<void> startSync(TaskStore store) async {
  await Device.init();
  switch (kEdition) {
    case Edition.normal:
      lanServer = LanServer(store);
      await lanServer!.start();
    case Edition.dev:
      lanClient = LanClient(store);
      await lanClient!.start();
    case Edition.online:
      cloud = CloudSync(store);
      await cloud!.start();
  }
}

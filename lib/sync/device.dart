import 'package:shared_preferences/shared_preferences.dart';

import '../utils.dart';

/// Identidade deste aparelho na rede.
class Device {
  static late String id;
  static late String name;
  static late SharedPreferences prefs;

  static Future<void> init() async {
    prefs = await SharedPreferences.getInstance();
    id = prefs.getString('device_id_v1') ?? newUid();
    await prefs.setString('device_id_v1', id);
    name = prefs.getString('device_name_v1') ?? 'Celular ${id.substring(0, 4)}';
  }

  static Future<void> rename(String n) async {
    name = n.trim().isEmpty ? name : n.trim();
    await prefs.setString('device_name_v1', name);
  }
}

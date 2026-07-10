import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Sur Chrome, flutter_secure_storage peut prendre plusieurs minutes (Web Crypto).
/// Web → SharedPreferences (instantané). Mobile natif → stockage sécurisé.
class TokenStorage {
  static const _keys = ['access_token', 'user', 'portal'];
  static SharedPreferences? _prefs;
  static const _secure = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static Future<void> init() async {
    if (kIsWeb) {
      _prefs = await SharedPreferences.getInstance();
    }
  }

  static Future<void> write(String key, String value) async {
    if (kIsWeb) {
      await _prefs?.setString(key, value);
      return;
    }
    await _secure.write(key: key, value: value);
  }

  static Future<String?> read(String key) async {
    if (kIsWeb) {
      return _prefs?.getString(key);
    }
    return _secure.read(key: key);
  }

  static Future<void> deleteAll() async {
    if (kIsWeb) {
      for (final key in _keys) {
        await _prefs?.remove(key);
      }
      return;
    }
    await _secure.deleteAll();
  }
}

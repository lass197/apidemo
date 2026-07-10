import 'package:flutter/foundation.dart';

/// URL de l'API — surchargeable au lancement :
/// flutter run -d chrome --dart-define=API_BASE=http://192.168.1.10:8000/api/v1
class ApiConfig {
  static const _override = String.fromEnvironment('API_BASE', defaultValue: '');

  static String get baseUrl {
    if (_override.isNotEmpty) return _override;
    if (kIsWeb) return 'http://localhost:8000/api/v1';
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000/api/v1';
      default:
        return 'http://localhost:8000/api/v1';
    }
  }
}

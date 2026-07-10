import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';

class ApiHttp {
  static const Duration timeout = Duration(seconds: 15);

  static String timeoutMessage() =>
      'Serveur inaccessible (${ApiConfig.baseUrl}). '
      'Vérifiez que le backend Django tourne : python manage.py runserver';

  static String networkMessage() =>
      'Impossible de joindre l\'API (${ApiConfig.baseUrl}). '
      'Lancez le backend sur le port 8000 puis réessayez.';

  static Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    try {
      return await http
          .post(url, headers: headers, body: body)
          .timeout(timeout);
    } on TimeoutException {
      throw ApiHttpException(timeoutMessage());
    } on http.ClientException {
      throw ApiHttpException(networkMessage());
    }
  }

  static Future<http.Response> get(Uri url, {Map<String, String>? headers}) async {
    try {
      return await http.get(url, headers: headers).timeout(timeout);
    } on TimeoutException {
      throw ApiHttpException(timeoutMessage());
    } on http.ClientException {
      throw ApiHttpException(networkMessage());
    }
  }
}

class ApiHttpException implements Exception {
  final String message;
  ApiHttpException(this.message);

  @override
  String toString() => message;
}

String? parseApiDetail(http.Response response, String fallback) {
  try {
    final body = jsonDecode(response.body);
    if (body is Map && body['detail'] != null) return body['detail'].toString();
  } catch (_) {}
  return fallback;
}

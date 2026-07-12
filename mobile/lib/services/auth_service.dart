import 'dart:convert';

import 'api_http.dart';
import '../config/api_config.dart';
import 'token_storage.dart';

enum PortalType { patient, doctor }

class AuthApiResult {
  final bool ok;
  final Map<String, dynamic>? data;
  final String? error;

  const AuthApiResult._({required this.ok, this.data, this.error});

  factory AuthApiResult.success(Map<String, dynamic> data) =>
      AuthApiResult._(ok: true, data: data);

  factory AuthApiResult.failure(String error) =>
      AuthApiResult._(ok: false, error: error);
}

class AuthService {
  static String get _baseUrl => ApiConfig.baseUrl;

  static Future<AuthApiResult> loginWithResult(
    String username,
    String password, {
    String? loginOtp,
    String? challengeId,
  }) async {
    try {
      final body = <String, dynamic>{
        'username': username,
        'password': password,
      };
      if (loginOtp != null && loginOtp.isNotEmpty) {
        body['login_otp'] = loginOtp;
        body['challenge_id'] = challengeId;
      }
      final response = await ApiHttp.post(
        Uri.parse('$_baseUrl/auth/login/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );
      if (response.statusCode != 200) {
        return AuthApiResult.failure(parseApiDetail(response, 'Connexion échouée')!);
      }
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (data['requires_otp'] == true) {
        return AuthApiResult.success(data);
      }
      final token = data['access_token'] as String?;
      if (token == null || token.isEmpty) {
        return AuthApiResult.failure('Réponse de connexion invalide.');
      }
      await TokenStorage.write('access_token', token);
      await TokenStorage.write('user', jsonEncode(data['user']));
      return AuthApiResult.success(data);
    } on ApiHttpException catch (e) {
      return AuthApiResult.failure(e.message);
    }
  }

  static Future<Map<String, dynamic>?> login(String username, String password) async {
    final result = await loginWithResult(username, password);
    return result.ok ? result.data : null;
  }

  static Future<AuthApiResult> registerPatient({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    required String dateOfBirth,
    required String gender,
    required String phone,
    String? username,
  }) async {
    final payload = <String, dynamic>{
      'email': email,
      'password': password,
      'first_name': firstName,
      'last_name': lastName,
      'date_of_birth': dateOfBirth,
      'gender': gender,
      'phone': phone,
    };
    if (username != null && username.isNotEmpty) payload['username'] = username;

    try {
      final response = await ApiHttp.post(
        Uri.parse('$_baseUrl/auth/register/patient/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );
      if (response.statusCode != 200) {
        return AuthApiResult.failure(parseApiDetail(response, 'Inscription impossible.')!);
      }
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final token = data['access_token'] as String?;
      if (token != null && token.isNotEmpty) {
        await TokenStorage.write('access_token', token);
        await TokenStorage.write('user', jsonEncode(data['user']));
        await TokenStorage.write('portal', PortalType.patient.name);
      }
      return AuthApiResult.success(data);
    } on ApiHttpException catch (e) {
      return AuthApiResult.failure(e.message);
    }
  }

  static Future<AuthApiResult> verifyRegistrationOtp({
    required String email,
    required String code,
    required String password,
  }) async {
    try {
      final response = await ApiHttp.post(
        Uri.parse('$_baseUrl/auth/register/patient/verify-otp/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'code': code, 'password': password}),
      );
      if (response.statusCode != 200) {
        return AuthApiResult.failure(parseApiDetail(response, 'Code invalide.')!);
      }
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await TokenStorage.write('access_token', data['access_token'] as String);
      await TokenStorage.write('user', jsonEncode(data['user']));
      await TokenStorage.write('portal', PortalType.patient.name);
      return AuthApiResult.success(data);
    } on ApiHttpException catch (e) {
      return AuthApiResult.failure(e.message);
    }
  }

  static Future<AuthApiResult> resendRegistrationOtp(String email) async {
    try {
      final response = await ApiHttp.post(
        Uri.parse('$_baseUrl/auth/register/patient/resend-otp/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email.trim().toLowerCase()}),
      );
      if (response.statusCode != 200) {
        return AuthApiResult.failure(parseApiDetail(response, 'Renvoi impossible.')!);
      }
      return AuthApiResult.success(jsonDecode(response.body) as Map<String, dynamic>);
    } on ApiHttpException catch (e) {
      return AuthApiResult.failure(e.message);
    }
  }

  static Future<bool> isLoggedIn() async {
    final token = await TokenStorage.read('access_token');
    return token != null && token.isNotEmpty;
  }

  static Future<String?> getToken() => TokenStorage.read('access_token');

  static Future<Map<String, dynamic>?> getUser() async {
    final raw = await TokenStorage.read('user');
    if (raw == null) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  static List<String> rolesFromUser(Map<String, dynamic>? user) {
    if (user == null) return [];
    final roles = user['roles'];
    if (roles is List) return roles.map((r) => r.toString()).toList();
    return [];
  }

  static bool isPatient(Map<String, dynamic>? user) => rolesFromUser(user).contains('PATIENT');

  static bool isDoctor(Map<String, dynamic>? user) => rolesFromUser(user).contains('DOCTOR');

  static Future<PortalType?> getPortal() async {
    final raw = await TokenStorage.read('portal');
    if (raw == null) return null;
    return PortalType.values.firstWhere(
      (p) => p.name == raw,
      orElse: () => PortalType.patient,
    );
  }

  static Future<void> setPortal(PortalType portal) async {
    await TokenStorage.write('portal', portal.name);
  }

  static Future<PortalType?> resolvePortal() async {
    final stored = await getPortal();
    if (stored != null) return stored;
    final user = await getUser();
    if (isDoctor(user)) return PortalType.doctor;
    if (isPatient(user)) return PortalType.patient;
    return null;
  }

  static Future<void> logout() async {
    await TokenStorage.deleteAll();
  }
}

class ApiService {
  static String get _baseUrl => ApiConfig.baseUrl;

  static Future<Map<String, String>> _headers() async {
    final token = await AuthService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static Future<Map<String, dynamic>?> getPatientProfile() async {
    try {
      final response = await ApiHttp.get(
        Uri.parse('$_baseUrl/clinical/patients/me/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } on ApiHttpException {
      return null;
    }
    return null;
  }

  static Future<List<dynamic>> getMyPatientAppointments() async {
    try {
      final response = await ApiHttp.get(
        Uri.parse('$_baseUrl/hr/appointments/patient/me/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    } on ApiHttpException {
      return [];
    }
    return [];
  }

  static Future<List<dynamic>> getAppointments(String patientId) async {
    try {
      final response = await ApiHttp.get(
        Uri.parse('$_baseUrl/hr/appointments/patient/$patientId/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    } on ApiHttpException {
      return [];
    }
    return [];
  }

  static Future<List<dynamic>> getDoctorAppointments() async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/appointments/mine/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<dynamic>> getDoctorPatients() async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/appointments/mine/patients/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<dynamic>> getDoctors() async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/doctors/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<dynamic>> getHospitalServices() async {
    final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/services/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<dynamic>> getAvailableSlots(String doctorId) async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/availabilities/$doctorId/slots/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<dynamic>> getCareTasks(String patientId) async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/clinical/care-tasks/patient/$patientId/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<bool> bookAppointment({
    required String patientId,
    required String doctorId,
    required String scheduledAt,
    String reason = '',
    String? serviceId,
  }) async {
      final response = await ApiHttp.post(
      Uri.parse('$_baseUrl/hr/appointments/'),
      headers: await _headers(),
      body: jsonEncode({
        'patient_id': patientId,
        'doctor_id': doctorId,
        'scheduled_at': scheduledAt,
        'reason': reason,
        if (serviceId != null && serviceId.isNotEmpty) 'service_id': serviceId,
      }),
    );
    return response.statusCode == 200;
  }

  static Future<List<dynamic>> getDocuments({String? patientId}) async {
    final uri = patientId != null
        ? Uri.parse('$_baseUrl/documents/?patient_id=$patientId')
        : Uri.parse('$_baseUrl/documents/');
      final response = await ApiHttp.get(uri, headers: await _headers());
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<int>?> downloadPatientIdentityPdf({String? doctorId}) async {
    try {
      var url = '$_baseUrl/clinical/patients/me/identity-pdf/';
      if (doctorId != null && doctorId.isNotEmpty) {
        url += '?doctor_id=$doctorId';
      }
      final response = await ApiHttp.get(
        Uri.parse(url),
        headers: await _headers(),
      );
      if (response.statusCode == 200) return response.bodyBytes;
    } on ApiHttpException {
      return null;
    }
    return null;
  }

  static Future<List<int>?> downloadDocument(String documentId) async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/documents/$documentId/download/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return response.bodyBytes;
    return null;
  }

  static Future<List<dynamic>> getChat(String patientId) async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/chat/$patientId/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<bool> sendChat(String patientId, String content) async {
      final response = await ApiHttp.post(
      Uri.parse('$_baseUrl/hr/chat/'),
      headers: await _headers(),
      body: jsonEncode({'patient_id': patientId, 'content': content}),
    );
    return response.statusCode == 200;
  }

  static Future<List<dynamic>> getReminders(String patientId) async {
      final response = await ApiHttp.get(
      Uri.parse('$_baseUrl/hr/reminders/patient/$patientId/'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    return [];
  }

  static Future<List<dynamic>> getMyInvoices() async {
    try {
      final response = await ApiHttp.get(
        Uri.parse('$_baseUrl/billing/invoices/mine/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    } on ApiHttpException {
      return [];
    }
    return [];
  }

  static Future<List<dynamic>> getMyInvoiceLines(String invoiceId) async {
    try {
      final response = await ApiHttp.get(
        Uri.parse('$_baseUrl/billing/invoices/mine/$invoiceId/lines/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) return jsonDecode(response.body) as List<dynamic>;
    } on ApiHttpException {
      return [];
    }
    return [];
  }

  static Future<({bool ok, String? error, Map<String, dynamic>? invoice})> declareInvoicePayment({
    required String invoiceId,
    required String phoneNumber,
    required String method,
    required String declaration,
    String transactionReference = '',
  }) async {
    try {
      final response = await ApiHttp.post(
        Uri.parse('$_baseUrl/billing/invoices/mine/$invoiceId/declare/'),
        headers: await _headers(),
        body: jsonEncode({
          'phone_number': phoneNumber,
          'method': method,
          'declaration': declaration,
          'transaction_reference': transactionReference,
        }),
      );
      if (response.statusCode == 200) {
        return (ok: true, error: null, invoice: jsonDecode(response.body) as Map<String, dynamic>);
      }
      return (ok: false, error: parseApiDetail(response, 'Déclaration impossible'), invoice: null);
    } on ApiHttpException catch (e) {
      return (ok: false, error: e.message, invoice: null);
    }
  }
}

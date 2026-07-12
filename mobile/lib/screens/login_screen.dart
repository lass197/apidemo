import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/auth_service.dart';
import '../utils/form_validators.dart';
import '../widgets/app_form_field.dart';
import '../widgets/sghl_form_fields.dart';
import 'doctor_home_screen.dart';
import 'patient_home_screen.dart';
import 'portal_screen.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  final PortalType portal;

  const LoginScreen({super.key, required this.portal});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _username;
  late final TextEditingController _password;
  final _otpCode = TextEditingController();
  bool _loading = false;
  String _error = '';
  int _step = 1;
  String _otpDevCode = '';
  String _challengeId = '';

  @override
  void initState() {
    super.initState();
    if (widget.portal == PortalType.doctor) {
      _username = TextEditingController(text: 'dr.martin');
      _password = TextEditingController(text: 'Medecin@2026');
    } else {
      _username = TextEditingController(text: 'alice.moreau');
      _password = TextEditingController(text: 'Patient@2026');
    }
  }

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    _otpCode.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    setState(() => _error = '');
    if (_step == 1 && !_formKey.currentState!.validate()) {
      setState(() => _error = 'Corrigez le champ signalé ci-dessous.');
      return;
    }
    if (_step == 2 && !RegExp(r'^\d{6}$').hasMatch(_otpCode.text.trim())) {
      setState(() => _error = 'Saisissez le code à 6 chiffres affiché.');
      return;
    }

    setState(() => _loading = true);

    final loginId = widget.portal == PortalType.patient
        ? _username.text.trim().toLowerCase()
        : _username.text.trim();

    final result = await AuthService.loginWithResult(
      loginId,
      _password.text,
      loginOtp: _step == 2 ? _otpCode.text.trim() : null,
      challengeId: _step == 2 ? _challengeId : null,
    );
    if (!mounted) return;

    if (!result.ok) {
      setState(() {
        _error = result.error ?? 'Connexion échouée';
        _loading = false;
      });
      return;
    }

    final data = result.data!;
    if (data['requires_otp'] == true && widget.portal == PortalType.patient) {
      setState(() {
        _step = 2;
        _challengeId = (data['challenge_id'] as String?) ?? '';
        _otpDevCode = (data['otp_dev_code'] as String?) ?? '';
        _otpCode.clear();
        _loading = false;
      });
      return;
    }

    final user = data['user'] as Map<String, dynamic>?;
    if (widget.portal == PortalType.doctor && !AuthService.isDoctor(user)) {
      await AuthService.logout();
      setState(() {
        _error = 'Ce compte n\'est pas un profil médecin.';
        _loading = false;
      });
      return;
    }
    if (widget.portal == PortalType.patient && !AuthService.isPatient(user)) {
      await AuthService.logout();
      setState(() {
        _error = 'Ce compte n\'est pas un profil patient.';
        _loading = false;
      });
      return;
    }

    await AuthService.setPortal(widget.portal);
    if (!mounted) return;

    final home = widget.portal == PortalType.doctor
        ? const DoctorHomeScreen()
        : const PatientHomeScreen();
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => home),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDoctor = widget.portal == PortalType.doctor;
    final isPatient = widget.portal == PortalType.patient;

    return Scaffold(
      appBar: AppBar(
        title: Text(isDoctor ? 'Personnel hospitalier' : 'Espace patient'),
        backgroundColor: isDoctor ? const Color(0xFF134E4A) : const Color(0xFF475569),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                autovalidateMode: AutovalidateMode.onUserInteraction,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Icon(
                      isDoctor ? Icons.medical_services_rounded : Icons.person_rounded,
                      size: 64,
                      color: isDoctor ? const Color(0xFF0D9488) : const Color(0xFF475569),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      isPatient && _step == 2 ? 'Confirmation' : (isDoctor ? 'Personnel hospitalier' : 'Espace patient'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      isPatient && _step == 2
                          ? 'Validez le code affiché pour entrer'
                          : (isDoctor ? 'Connexion staff SGHL' : 'Rendez-vous, résultats, soins'),
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 24),
                    if (_otpDevCode.isNotEmpty && _step == 2) ...[
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.teal.shade50,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.teal.shade200),
                        ),
                        child: Column(
                          children: [
                            const Text('Code de connexion', style: TextStyle(fontWeight: FontWeight.w600)),
                            const SizedBox(height: 8),
                            Text(
                              _otpDevCode,
                              style: TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 8,
                                color: Colors.teal.shade900,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Saisissez ce code ci-dessous pour confirmer votre connexion.',
                              textAlign: TextAlign.center,
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    if (_error.isNotEmpty) ...[AppErrorBanner(message: _error), const SizedBox(height: 16)],
                    if (_step == 1) ...[
                      SghlTextFormField(
                        controller: _username,
                        labelText: isPatient ? 'Email' : 'Identifiant',
                        required: true,
                        keyboardType: isPatient ? TextInputType.emailAddress : TextInputType.text,
                        validator: isPatient ? FormValidators.email : FormValidators.required,
                      ),
                      const SizedBox(height: 12),
                      SghlTextFormField(
                        controller: _password,
                        labelText: 'Mot de passe',
                        required: true,
                        obscureText: true,
                        validator: FormValidators.required,
                      ),
                    ] else ...[
                      SghlTextFormField(
                        controller: _otpCode,
                        labelText: 'Code à 6 chiffres',
                        required: true,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                        textAlign: TextAlign.center,
                      ),
                    ],
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _loading ? null : _login,
                      child: Text(_loading
                          ? 'Patientez…'
                          : (_step == 2 ? 'Confirmer la connexion' : 'Se connecter')),
                    ),
                    if (_step == 2) ...[
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: () => setState(() {
                          _step = 1;
                          _otpDevCode = '';
                          _challengeId = '';
                          _otpCode.clear();
                          _error = '';
                        }),
                        child: const Text('← Modifier email / mot de passe'),
                      ),
                    ],
                    if (isPatient && _step == 1) ...[
                      const SizedBox(height: 16),
                      TextButton(
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const RegisterScreen()),
                        ),
                        child: const Text('Créer un compte patient'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

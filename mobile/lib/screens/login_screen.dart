import 'package:flutter/material.dart';

import '../services/auth_service.dart';
import '../utils/form_validators.dart';
import '../widgets/app_form_field.dart';
import '../widgets/sghl_form_fields.dart';
import 'doctor_home_screen.dart';
import 'patient_home_screen.dart';
import 'portal_screen.dart';
import 'register_screen.dart';
import 'verify_screen.dart';

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
  bool _loading = false;
  String _error = '';

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
    super.dispose();
  }

  Future<void> _login() async {
    setState(() {
      _error = '';
    });
    if (!_formKey.currentState!.validate()) {
      setState(() => _error = 'Corrigez le champ signalé ci-dessous.');
      return;
    }

    setState(() => _loading = true);

    final loginId = widget.portal == PortalType.patient
        ? _username.text.trim().toLowerCase()
        : _username.text.trim();

    final result = await AuthService.loginWithResult(loginId, _password.text);
    if (!mounted) return;

    if (!result.ok) {
      setState(() {
        _error = result.error ?? 'Connexion échouée';
        _loading = false;
      });
      return;
    }

    final user = result.data!['user'] as Map<String, dynamic>?;
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
                      isDoctor ? 'Personnel hospitalier' : 'Espace patient',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      isDoctor ? 'Connexion staff SGHL' : 'Rendez-vous, résultats, soins',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 24),
                    if (_error.isNotEmpty) ...[AppErrorBanner(message: _error), const SizedBox(height: 16)],
                    SghlTextFormField(
                      controller: _username,
                      labelText: isPatient ? 'Email' : 'Identifiant',
                      hintText: isPatient ? 'votre.email@exemple.com' : null,
                      helperText: isPatient ? 'L\'adresse utilisée à l\'inscription' : null,
                      required: true,
                      keyboardType: isPatient ? TextInputType.emailAddress : TextInputType.text,
                      autofillHints: isPatient ? const [AutofillHints.email] : const [AutofillHints.username],
                      validator: (v) {
                        if (isPatient) {
                          final msg = FormValidators.loginIdentifier(v, isPatient: true);
                          return msg.isEmpty ? null : msg;
                        }
                        if (v == null || v.trim().isEmpty) return 'Identifiant est obligatoire.';
                        return null;
                      },
                      textInputAction: TextInputAction.next,
                    ),
                    const SizedBox(height: 16),
                    SghlTextFormField(
                      controller: _password,
                      labelText: 'Mot de passe',
                      required: true,
                      obscureText: true,
                      autofillHints: const [AutofillHints.password],
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _login(),
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Mot de passe est obligatoire.' : null,
                    ),
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _loading ? null : _login,
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        backgroundColor: isDoctor ? const Color(0xFF0D9488) : const Color(0xFF475569),
                      ),
                      child: _loading
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Se connecter'),
                    ),
                    const SizedBox(height: 16),
                    if (isPatient)
                      Wrap(
                        alignment: WrapAlignment.center,
                        children: [
                          const Text('Pas encore de compte ? ', style: TextStyle(fontSize: 12, color: Colors.grey)),
                          TextButton(
                            onPressed: _loading
                                ? null
                                : () => Navigator.push(
                                      context,
                                      MaterialPageRoute(builder: (_) => const RegisterScreen()),
                                    ),
                            child: const Text('Créer un compte'),
                          ),
                          const Text(' · ', style: TextStyle(color: Colors.grey)),
                          TextButton(
                            onPressed: _loading
                                ? null
                                : () => Navigator.push(
                                      context,
                                      MaterialPageRoute(builder: (_) => const VerifyScreen()),
                                    ),
                            child: const Text('Code reçu ?'),
                          ),
                        ],
                      ),
                    TextButton(
                      onPressed: _loading
                          ? null
                          : () => Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(builder: (_) => const PortalScreen()),
                              ),
                      child: const Text('← Changer d\'espace'),
                    ),
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

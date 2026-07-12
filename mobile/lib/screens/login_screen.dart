import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/auth_service.dart';
import '../theme/sghl_theme.dart';
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
    final headerColor = isDoctor ? SghlTheme.tealDark : SghlTheme.slate;

    return Scaffold(
      body: Column(
        children: [
          Container(
            width: double.infinity,
            padding: EdgeInsets.only(
              top: MediaQuery.paddingOf(context).top + 8,
              left: 8,
              right: 24,
              bottom: 28,
            ),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: isDoctor
                    ? const [SghlTheme.tealDark, SghlTheme.teal]
                    : const [SghlTheme.slate, Color(0xFF334155)],
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(
                          isDoctor ? Icons.medical_services_rounded : Icons.person_rounded,
                          color: Colors.white,
                          size: 28,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'SGHL',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 1,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              isPatient && _step == 2
                                  ? 'Confirmation'
                                  : (isDoctor ? 'Personnel hospitalier' : 'Espace patient'),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 22,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              isPatient && _step == 2
                                  ? 'Validez le code affiché pour entrer'
                                  : (isDoctor ? 'Connexion staff' : 'Rendez-vous, résultats, soins'),
                              style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Container(
              color: SghlTheme.canvas,
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Material(
                      color: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                        side: BorderSide(color: Colors.black.withValues(alpha: 0.06)),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Form(
                          key: _formKey,
                          autovalidateMode: AutovalidateMode.onUserInteraction,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              if (_otpDevCode.isNotEmpty && _step == 2) ...[
                                Container(
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFECFDF5),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: SghlTheme.teal.withValues(alpha: 0.35)),
                                  ),
                                  child: Column(
                                    children: [
                                      Text(
                                        'Code de connexion',
                                        style: TextStyle(
                                          fontWeight: FontWeight.w600,
                                          color: headerColor,
                                        ),
                                      ),
                                      const SizedBox(height: 10),
                                      Text(
                                        _otpDevCode,
                                        style: const TextStyle(
                                          fontSize: 34,
                                          fontWeight: FontWeight.bold,
                                          letterSpacing: 10,
                                          color: SghlTheme.tealDark,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        'Saisissez ce code ci-dessous pour confirmer.',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 20),
                              ],
                              if (_error.isNotEmpty) ...[
                                AppErrorBanner(message: _error),
                                const SizedBox(height: 16),
                              ],
                              if (_step == 1) ...[
                                SghlTextFormField(
                                  controller: _username,
                                  labelText: isPatient ? 'Email' : 'Identifiant',
                                  required: true,
                                  keyboardType: isPatient ? TextInputType.emailAddress : TextInputType.text,
                                  validator: isPatient ? FormValidators.email : FormValidators.required,
                                ),
                                const SizedBox(height: 14),
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
                                child: Text(
                                  _loading
                                      ? 'Patientez…'
                                      : (_step == 2 ? 'Confirmer la connexion' : 'Se connecter'),
                                ),
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
                                const SizedBox(height: 12),
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
              ),
            ),
          ),
        ],
      ),
    );
  }
}

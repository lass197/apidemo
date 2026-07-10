import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/auth_service.dart';
import '../utils/form_validators.dart';
import '../widgets/app_form_field.dart';
import '../widgets/sghl_form_fields.dart';
import 'patient_home_screen.dart';

class VerifyScreen extends StatefulWidget {
  const VerifyScreen({super.key});

  @override
  State<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends State<VerifyScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _otpCode = TextEditingController();
  bool _loading = false;
  String _error = '';
  String _success = '';

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _otpCode.dispose();
    super.dispose();
  }

  Future<void> _resend() async {
    setState(() {
      _error = '';
      _success = '';
    });
    final emailErr = FormValidators.email(_email.text, required: true);
    if (emailErr.isNotEmpty) {
      setState(() => _error = 'Corrigez l\'email ci-dessous.');
      return;
    }
    setState(() => _loading = true);
    final result = await AuthService.resendRegistrationOtp(_email.text.trim().toLowerCase());
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok) {
      setState(() => _success = 'Un nouveau code a été envoyé. Vérifiez votre boîte mail (et les spams).');
    } else {
      setState(() => _error = result.error ?? 'Envoi impossible.');
    }
  }

  Future<void> _verify() async {
    setState(() {
      _error = '';
      _success = '';
    });
    if (!_formKey.currentState!.validate()) {
      setState(() => _error = 'Corrigez les champs signalés.');
      return;
    }
    setState(() => _loading = true);
    final result = await AuthService.verifyRegistrationOtp(
      email: _email.text.trim().toLowerCase(),
      code: _otpCode.text.trim(),
      password: _password.text,
    );
    if (!mounted) return;
    if (result.ok) {
      await AuthService.setPortal(PortalType.patient);
      if (!mounted) return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const PatientHomeScreen()),
        (_) => false,
      );
    } else {
      setState(() {
        _error = result.error ?? 'Vérification impossible.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Activer mon compte')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Form(
              key: _formKey,
              autovalidateMode: AutovalidateMode.onUserInteraction,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Saisissez le code reçu par email',
                    style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                  ),
                  const SizedBox(height: 16),
                  if (_error.isNotEmpty) ...[AppErrorBanner(message: _error), const SizedBox(height: 12)],
                  if (_success.isNotEmpty) ...[AppSuccessBanner(message: _success), const SizedBox(height: 12)],
                  SghlTextFormField(
                    controller: _email,
                    labelText: 'Email',
                    hintText: 'exemple@email.com',
                    helperText: 'Même adresse qu\'à l\'inscription',
                    required: true,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    validator: (v) {
                      final msg = FormValidators.email(v, required: true);
                      return msg.isEmpty ? null : msg;
                    },
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: 16),
                  SghlTextFormField(
                    controller: _password,
                    labelText: 'Mot de passe (celui choisi à l\'inscription)',
                    required: true,
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    validator: (v) {
                      final msg = FormValidators.password(v);
                      return msg.isEmpty ? null : msg;
                    },
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: 16),
                  SghlTextFormField(
                    controller: _otpCode,
                    labelText: 'Code à 6 chiffres',
                    hintText: '000000',
                    required: true,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 24, letterSpacing: 8, fontFamily: 'monospace'),
                    validator: (v) {
                      if (v == null || !RegExp(r'^\d{6}$').hasMatch(v.trim())) {
                        return 'Code à 6 chiffres requis.';
                      }
                      return null;
                    },
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => _verify(),
                  ),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _loading ? null : _verify,
                    child: _loading
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Activer mon compte'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: _loading ? null : _resend,
                    child: const Text('Renvoyer le code'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

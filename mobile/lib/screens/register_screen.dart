import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/phone_countries.dart';
import '../services/auth_service.dart';
import '../utils/form_validators.dart';
import '../widgets/app_form_field.dart';
import '../widgets/phone_input.dart';
import '../widgets/sghl_form_fields.dart';
import 'login_screen.dart';
import 'patient_home_screen.dart';
import 'verify_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKeyStep1 = GlobalKey<FormState>();
  final _formKeyStep2 = GlobalKey<FormState>();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _email = TextEditingController();
  final _username = TextEditingController();
  final _password = TextEditingController();
  final _passwordConfirm = TextEditingController();
  final _otpCode = TextEditingController();

  String _dateOfBirth = '';
  String _gender = 'F';
  String _phone = '';
  int _step = 1;
  bool _loading = false;
  String _error = '';
  String _pendingEmail = '';
  String _otpDevCode = '';
  List<PhoneCountry> _countries = [];

  @override
  void initState() {
    super.initState();
    PhoneCountries.load().then((c) {
      if (mounted) setState(() => _countries = c);
    });
  }

  @override
  void dispose() {
    _firstName.dispose();
    _lastName.dispose();
    _email.dispose();
    _username.dispose();
    _password.dispose();
    _passwordConfirm.dispose();
    _otpCode.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final initial = _dateOfBirth.isNotEmpty ? DateTime.tryParse(_dateOfBirth) : DateTime(1990);
    final d = await showDatePicker(
      context: context,
      initialDate: initial ?? DateTime(1990),
      firstDate: DateTime(1920),
      lastDate: DateTime.now(),
      helpText: 'Date de naissance',
    );
    if (d != null) {
      setState(() {
        _dateOfBirth =
            '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
      });
    }
  }

  Future<void> _submitRegister() async {
    setState(() => _error = '');
    if (!_formKeyStep1.currentState!.validate()) {
      setState(() => _error = 'Corrigez les champs signalés ci-dessous.');
      return;
    }
    if (_dateOfBirth.isEmpty) {
      setState(() => _error = 'Corrigez les champs signalés ci-dessous.');
      return;
    }
    setState(() => _loading = true);
    final result = await AuthService.registerPatient(
      email: _email.text.trim().toLowerCase(),
      password: _password.text,
      firstName: _firstName.text.trim(),
      lastName: _lastName.text.trim(),
      dateOfBirth: _dateOfBirth,
      gender: _gender,
      phone: _phone.trim(),
      username: _username.text.trim().isEmpty ? null : _username.text.trim().toLowerCase(),
    );
    if (!mounted) return;
    if (result.ok) {
      final data = result.data!;
      final devCode = data['otp_dev_code'] as String?;
      setState(() {
        _step = 2;
        _pendingEmail = (data['email'] as String?) ?? _email.text.trim().toLowerCase();
        _otpDevCode = devCode ?? '';
        if (_otpDevCode.isNotEmpty) {
          _otpCode.text = _otpDevCode;
        }
        _loading = false;
      });
    } else {
      setState(() {
        _error = result.error ?? 'Inscription impossible.';
        _loading = false;
      });
    }
  }

  Future<void> _verifyOtp() async {
    setState(() => _error = '');
    if (!_formKeyStep2.currentState!.validate()) return;
    setState(() => _loading = true);
    final result = await AuthService.verifyRegistrationOtp(
      email: _pendingEmail,
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
        _error = result.error ?? 'Code invalide.';
        _loading = false;
      });
    }
  }

  Future<void> _resendOtp() async {
    setState(() {
      _error = '';
      _loading = true;
    });
    final result = await AuthService.resendRegistrationOtp(_pendingEmail);
    if (!mounted) return;
    setState(() => _loading = false);
    if (result.ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Un nouveau code a été envoyé.')),
      );
    } else {
      setState(() => _error = result.error ?? 'Renvoi impossible.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_step == 1 ? 'Créer un compte patient' : 'Vérification email'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: _step == 1 ? _buildStep1() : _buildStep2(),
          ),
        ),
      ),
    );
  }

  Widget _buildStep1() {
    return Form(
      key: _formKeyStep1,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Email unique — accès rendez-vous, résultats et plan de soins',
            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          if (_error.isNotEmpty) ...[AppErrorBanner(message: _error), const SizedBox(height: 16)],
          SghlTextFormField(
            controller: _firstName,
            labelText: 'Prénom',
            required: true,
            inputFormatters: [FilteringTextInputFormatter.deny(RegExp(r'\d'))],
            validator: (v) {
              final msg = FormValidators.personName(v, 'Prénom');
              return msg.isEmpty ? null : msg;
            },
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 16),
          SghlTextFormField(
            controller: _lastName,
            labelText: 'Nom',
            required: true,
            inputFormatters: [FilteringTextInputFormatter.deny(RegExp(r'\d'))],
            validator: (v) {
              final msg = FormValidators.personName(v, 'Nom');
              return msg.isEmpty ? null : msg;
            },
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 16),
          SghlTextFormField(
            controller: _email,
            labelText: 'Email',
            hintText: 'exemple@email.com',
            helperText: 'Utilisé pour la connexion et le code de vérification',
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
            controller: _username,
            labelText: 'Identifiant',
            hintText: 'lettres et chiffres uniquement',
            helperText: 'Optionnel — sinon généré depuis l\'email',
            validator: (v) {
              final msg = FormValidators.optionalUsername(v);
              return msg.isEmpty ? null : msg;
            },
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 16),
          FormField<String>(
            autovalidateMode: AutovalidateMode.onUserInteraction,
            validator: (_) {
              final msg = FormValidators.dateOfBirth(_dateOfBirth.isEmpty ? null : _dateOfBirth);
              return msg.isEmpty ? null : msg;
            },
            builder: (state) => InkWell(
              onTap: () async {
                await _pickDate();
                state.didChange(_dateOfBirth);
                state.validate();
              },
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: 'Date de naissance *',
                  border: const OutlineInputBorder(),
                  errorText: state.errorText,
                ),
                child: Text(
                  _dateOfBirth.isEmpty ? 'Appuyez pour choisir une date' : _dateOfBirth,
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          SghlGenderFormField(
            value: _gender,
            onChanged: (v) => setState(() => _gender = v ?? 'F'),
          ),
          const SizedBox(height: 16),
          FormField<String>(
            initialValue: _phone,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            validator: (v) {
              if (_countries.isEmpty) return null;
              final msg = PhoneCountries.validateInternational(_countries, v, required: true);
              return msg.isEmpty ? null : msg;
            },
            builder: (state) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.only(bottom: 6),
                  child: Text(
                    'Téléphone mobile *',
                    style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                  ),
                ),
                PhoneInput(
                  value: state.value ?? '',
                  required: true,
                  error: state.errorText,
                  onChanged: (v) {
                    state.didChange(v);
                    _phone = v;
                  },
                  onBlur: () => state.validate(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SghlTextFormField(
            controller: _password,
            labelText: 'Mot de passe',
            helperText: 'Minimum 10 caractères',
            required: true,
            obscureText: true,
            autofillHints: const [AutofillHints.newPassword],
            validator: (v) {
              final msg = FormValidators.password(v);
              return msg.isEmpty ? null : msg;
            },
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 16),
          SghlTextFormField(
            controller: _passwordConfirm,
            labelText: 'Confirmer',
            required: true,
            obscureText: true,
            autofillHints: const [AutofillHints.newPassword],
            validator: (v) =>
                _password.text != v ? 'Les mots de passe ne correspondent pas.' : null,
            textInputAction: TextInputAction.done,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _submitRegister,
            child: _loading
                ? const SizedBox(
                    height: 22,
                    width: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Continuer'),
          ),
          const SizedBox(height: 16),
          Wrap(
            alignment: WrapAlignment.center,
            children: [
              const Text('Déjà inscrit ? ', style: TextStyle(fontSize: 13, color: Colors.grey)),
              TextButton(
                onPressed: () => Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const LoginScreen(portal: PortalType.patient)),
                ),
                child: const Text('Se connecter'),
              ),
              const Text(' · ', style: TextStyle(color: Colors.grey)),
              TextButton(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const VerifyScreen()),
                ),
                child: const Text('Code déjà reçu ?'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStep2() {
    return Form(
      key: _formKeyStep2,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Code envoyé à $_pendingEmail',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          if (_error.isNotEmpty) ...[AppErrorBanner(message: _error), const SizedBox(height: 16)],
          if (_otpDevCode.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.teal.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.teal.shade200),
              ),
              child: Text(
                'Mode démo — code : $_otpDevCode',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                  letterSpacing: 4,
                  color: Colors.teal.shade900,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
          const Center(child: Text('📧', style: TextStyle(fontSize: 40))),
          const SizedBox(height: 12),
          Text(
            _otpDevCode.isNotEmpty
                ? 'Entrez le code à 6 chiffres affiché ci-dessus pour activer votre compte.'
                : 'Entrez le code à 6 chiffres reçu par email pour activer votre compte.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          SghlTextFormField(
            controller: _otpCode,
            labelText: 'Code de vérification',
            hintText: '000000',
            required: true,
            keyboardType: TextInputType.number,
            maxLength: 6,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 24, letterSpacing: 8, fontFamily: 'monospace'),
            validator: (v) {
              if (v == null || !RegExp(r'^\d{6}$').hasMatch(v.trim())) {
                return 'Saisissez le code à 6 chiffres reçu par email.';
              }
              return null;
            },
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _verifyOtp,
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
            onPressed: _loading ? null : _resendOtp,
            child: const Text('Renvoyer le code'),
          ),
          TextButton(
            onPressed: () => setState(() => _step = 1),
            child: const Text('← Modifier mes informations'),
          ),
        ],
      ),
    );
  }
}

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

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _email = TextEditingController();
  final _username = TextEditingController();
  final _password = TextEditingController();
  final _passwordConfirm = TextEditingController();

  String _dateOfBirth = '';
  String _gender = 'F';
  String _phone = '';
  bool _loading = false;
  String _error = '';
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
    if (!_formKey.currentState!.validate()) {
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
      await AuthService.setPortal(PortalType.patient);
      if (!mounted) return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const PatientHomeScreen()),
        (_) => false,
      );
    } else {
      setState(() {
        _error = result.error ?? 'Inscription impossible.';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Créer un compte patient'),
        backgroundColor: const Color(0xFF475569),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: Center(
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
                    const Text(
                      'Accès immédiat à vos rendez-vous, résultats et soins',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.black54),
                    ),
                    const SizedBox(height: 20),
                    if (_error.isNotEmpty) ...[AppErrorBanner(message: _error), const SizedBox(height: 16)],
                    SghlTextFormField(
                      controller: _firstName,
                      labelText: 'Prénom',
                      required: true,
                      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r"[A-Za-zÀ-ÿ\s\-']"))],
                      validator: (v) => FormValidators.personName(v, 'Prénom'),
                    ),
                    const SizedBox(height: 12),
                    SghlTextFormField(
                      controller: _lastName,
                      labelText: 'Nom',
                      required: true,
                      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r"[A-Za-zÀ-ÿ\s\-']"))],
                      validator: (v) => FormValidators.personName(v, 'Nom'),
                    ),
                    const SizedBox(height: 12),
                    SghlTextFormField(
                      controller: _email,
                      labelText: 'Email',
                      required: true,
                      keyboardType: TextInputType.emailAddress,
                      validator: FormValidators.email,
                    ),
                    const SizedBox(height: 12),
                    SghlTextFormField(
                      controller: _username,
                      labelText: 'Identifiant (optionnel)',
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: _pickDate,
                      child: Text(_dateOfBirth.isEmpty ? 'Date de naissance *' : 'Naissance : $_dateOfBirth'),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _gender,
                      decoration: const InputDecoration(labelText: 'Genre', border: OutlineInputBorder()),
                      items: const [
                        DropdownMenuItem(value: 'F', child: Text('Féminin')),
                        DropdownMenuItem(value: 'M', child: Text('Masculin')),
                        DropdownMenuItem(value: 'O', child: Text('Autre')),
                      ],
                      onChanged: (v) => setState(() => _gender = v ?? 'F'),
                    ),
                    const SizedBox(height: 12),
                    PhoneInput(
                      countries: _countries,
                      onChanged: (v) => _phone = v,
                    ),
                    const SizedBox(height: 12),
                    SghlTextFormField(
                      controller: _password,
                      labelText: 'Mot de passe',
                      required: true,
                      obscureText: true,
                      validator: FormValidators.password,
                    ),
                    const SizedBox(height: 12),
                    SghlTextFormField(
                      controller: _passwordConfirm,
                      labelText: 'Confirmer',
                      required: true,
                      obscureText: true,
                      validator: (v) =>
                          v != _password.text ? 'Les mots de passe ne correspondent pas.' : null,
                    ),
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _loading ? null : _submitRegister,
                      child: Text(_loading ? 'Création…' : 'Créer mon compte'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const LoginScreen(portal: PortalType.patient),
                        ),
                      ),
                      child: const Text('Déjà inscrit ? Se connecter'),
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

/// Miroir de frontend/src/composables/useFormValidation.js
class FormValidators {
  static final _personNameRe = RegExp(r"^[a-zA-ZÀ-ÿ\s'-]+$");
  static final _emailRe = RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');

  /// Champ obligatoire (compatible TextFormField : null = OK).
  static String? required(String? value, [String field = 'Ce champ']) {
    if (value == null || value.trim().isEmpty) return '$field est obligatoire.';
    return null;
  }

  static String personName(String? value, [String field = 'Ce champ']) {
    final v = (value ?? '').trim();
    if (v.isEmpty) return '$field est obligatoire.';
    if (RegExp(r'\d').hasMatch(v)) return '$field : les chiffres ne sont pas autorisés.';
    if (!_personNameRe.hasMatch(v)) {
      return '$field : lettres, espaces, apostrophe et tiret uniquement.';
    }
    if (v.length < 2) return '$field : minimum 2 caractères.';
    return '';
  }

  static String email(String? value, {bool required = false}) {
    final v = (value ?? '').trim().toLowerCase();
    if (v.isEmpty) return required ? 'Email obligatoire.' : '';
    if (v.contains(' ')) return "L'email ne doit pas contenir d'espaces.";
    if (!v.contains('@') || !v.contains('.')) {
      return 'Format invalide : exemple nom@domaine.fr';
    }
    if (!_emailRe.hasMatch(v)) {
      return "Adresse email incorrecte. Vérifiez l'orthographe.";
    }
    final domain = v.split('@').length > 1 ? v.split('@')[1] : '';
    if (domain.isEmpty || domain.startsWith('.') || domain.endsWith('.')) {
      return 'Domaine email invalide (ex. @gmail.com).';
    }
    return '';
  }

  static String username(String? value) {
    final v = (value ?? '').trim().toLowerCase();
    if (v.isEmpty) return 'Identifiant obligatoire.';
    if (!RegExp(r'^[a-z0-9._-]{3,40}$').hasMatch(v)) {
      return 'Identifiant : 3–40 caractères (a-z, 0-9, . _ -).';
    }
    return '';
  }

  static String optionalUsername(String? value) {
    final v = (value ?? '').trim();
    if (v.isEmpty) return '';
    return username(v);
  }

  static String dateOfBirth(String? value) {
    if (value == null || value.isEmpty) return 'Date de naissance obligatoire.';
    final d = DateTime.tryParse(value);
    if (d == null) return 'Date invalide.';
    final today = DateTime.now();
    final todayDate = DateTime(today.year, today.month, today.day);
    if (d.isAfter(todayDate)) return 'La date ne peut pas être dans le futur.';
    if (todayDate.year - d.year > 120) return 'Date de naissance invalide.';
    return '';
  }

  static String password(String? value, {int min = 10}) {
    if (value == null || value.length < min) {
      return 'Mot de passe : minimum $min caractères.';
    }
    if (RegExp(r'^\d+$').hasMatch(value)) {
      return 'Le mot de passe ne peut pas être entièrement numérique.';
    }
    return '';
  }

  static String loginIdentifier(String? value, {bool isPatient = false}) {
    final v = (value ?? '').trim();
    if (v.isEmpty) {
      return isPatient ? 'Email ou identifiant obligatoire.' : 'Identifiant obligatoire.';
    }
    if (v.contains('@')) return email(v, required: true);
    return username(v);
  }
}

String stripDigitsFromName(String value) => value.replaceAll(RegExp(r'\d'), '');

bool hasFieldErrors(Map<String, String> errors) =>
    errors.values.any((e) => e.isNotEmpty);

Map<String, String> filterErrors(Map<String, String> errors) {
  return Map.fromEntries(errors.entries.where((e) => e.value.isNotEmpty));
}

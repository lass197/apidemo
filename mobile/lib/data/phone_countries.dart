import 'dart:convert';

import 'package:flutter/services.dart';

class PhoneCountry {
  final String code;
  final String name;
  final String dial;
  final String flag;
  final int min;
  final int max;
  final String example;

  const PhoneCountry({
    required this.code,
    required this.name,
    required this.dial,
    required this.flag,
    required this.min,
    required this.max,
    this.example = '',
  });

  factory PhoneCountry.fromJson(Map<String, dynamic> json) => PhoneCountry(
        code: json['code'] as String,
        name: json['name'] as String,
        dial: json['dial'] as String,
        flag: json['flag'] as String? ?? '',
        min: json['min'] as int,
        max: json['max'] as int,
        example: json['example'] as String? ?? '',
      );
}

class PhoneCountries {
  static List<PhoneCountry>? _cache;

  static Future<List<PhoneCountry>> load() async {
    if (_cache != null) return _cache!;
    final raw = await rootBundle.loadString('assets/data/phone_countries.json');
    final list = jsonDecode(raw) as List<dynamic>;
    _cache = list.map((e) => PhoneCountry.fromJson(e as Map<String, dynamic>)).toList();
    return _cache!;
  }

  static PhoneCountry findByCode(List<PhoneCountry> countries, String code) {
    return countries.firstWhere((c) => c.code == code, orElse: () => countries.first);
  }

  static ({PhoneCountry country, String national}) parseInternational(
    List<PhoneCountry> countries,
    String value,
  ) {
    final digits = value.replaceAll(RegExp(r'\D'), '');
    if (digits.isEmpty) {
      return (country: countries.first, national: '');
    }
    final sorted = [...countries]..sort((a, b) => b.dial.length.compareTo(a.dial.length));
    for (final c in sorted) {
      if (digits.startsWith(c.dial)) {
        return (country: c, national: digits.substring(c.dial.length));
      }
    }
    return (country: countries.first, national: digits);
  }

  static String formatE164(PhoneCountry country, String nationalDigits) {
    final n = nationalDigits.replaceAll(RegExp(r'\D'), '');
    if (n.isEmpty) return '';
    return '+${country.dial}$n';
  }

  static String validateInternational(List<PhoneCountry> countries, String? value, {bool required = false}) {
    final v = (value ?? '').trim();
    if (v.isEmpty) return required ? 'Téléphone obligatoire.' : '';
    if (!v.startsWith('+')) {
      return "Sélectionnez l'indicatif pays et saisissez uniquement des chiffres.";
    }
    final parsed = parseInternational(countries, v);
    if (parsed.national.isEmpty) return 'Numéro obligatoire (chiffres uniquement).';
    if (!RegExp(r'^\d+$').hasMatch(parsed.national)) {
      return 'Le numéro ne doit contenir que des chiffres.';
    }
    if (parsed.national.length < parsed.country.min || parsed.national.length > parsed.country.max) {
      final range = parsed.country.min == parsed.country.max
          ? '${parsed.country.min}'
          : '${parsed.country.min} à ${parsed.country.max}';
      return '${parsed.country.name} (+${parsed.country.dial}) : $range chiffres.';
    }
    return '';
  }

  static List<PhoneCountry> filter(List<PhoneCountry> countries, String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return countries;
    return countries.where((c) {
      return c.name.toLowerCase().contains(q) ||
          c.dial.contains(q.replaceAll(RegExp(r'\D'), '')) ||
          c.code.toLowerCase().contains(q);
    }).toList();
  }
}

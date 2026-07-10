import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/phone_countries.dart';
import 'app_form_field.dart';

class PhoneInput extends StatefulWidget {
  final String value;
  final ValueChanged<String> onChanged;
  final String? error;
  final bool required;
  final VoidCallback? onBlur;

  const PhoneInput({
    super.key,
    required this.value,
    required this.onChanged,
    this.error,
    this.required = false,
    this.onBlur,
  });

  @override
  State<PhoneInput> createState() => _PhoneInputState();
}

class _PhoneInputState extends State<PhoneInput> {
  List<PhoneCountry> _countries = [];
  PhoneCountry _country = const PhoneCountry(
    code: 'CG',
    name: 'République du Congo (RC)',
    dial: '242',
    flag: '🇨🇬',
    min: 9,
    max: 9,
  );
  String _national = '';
  final _countrySearch = TextEditingController();
  final _nationalCtrl = TextEditingController();
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _loadCountries();
  }

  @override
  void didUpdateWidget(covariant PhoneInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value && _loaded) {
      _applyExternalValue(widget.value);
    }
  }

  Future<void> _loadCountries() async {
    final countries = await PhoneCountries.load();
    if (!mounted) return;
    setState(() {
      _countries = countries;
      _loaded = true;
      _applyExternalValue(widget.value);
    });
  }

  void _applyExternalValue(String value) {
    if (_countries.isEmpty) return;
    final parsed = PhoneCountries.parseInternational(_countries, value);
    _country = parsed.country;
    _national = parsed.national;
    _nationalCtrl.text = _national;
    _countrySearch.text = '${_country.name} (+${_country.dial})';
  }

  void _syncEmit() {
    widget.onChanged(PhoneCountries.formatE164(_country, _national));
  }

  @override
  void dispose() {
    _countrySearch.dispose();
    _nationalCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) {
      return const SizedBox(height: 48, child: Center(child: CircularProgressIndicator(strokeWidth: 2)));
    }

    final filtered = PhoneCountries.filter(_countries, _countrySearch.text);
    final searchActive = _countrySearch.text.trim().isNotEmpty &&
        _countrySearch.text.trim() != '${_country.name} (+${_country.dial})';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          "Pays — tapez le nom, l'indicatif s'affiche",
          style: TextStyle(fontSize: 11, color: Colors.grey),
        ),
        const SizedBox(height: 4),
        TextField(
          controller: _countrySearch,
          decoration: const InputDecoration(
            hintText: 'Ex. Canada, France, Congo…',
            border: OutlineInputBorder(),
            isDense: true,
          ),
          onTap: () => setState(() {}),
          onChanged: (_) => setState(() {}),
          onEditingComplete: () {
            setState(() {});
            widget.onBlur?.call();
          },
        ),
        if (searchActive && filtered.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 8),
            constraints: const BoxConstraints(maxHeight: 160),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade300),
              borderRadius: BorderRadius.circular(12),
            ),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: filtered.length.clamp(0, 40),
              itemBuilder: (_, i) {
                final c = filtered[i];
                return ListTile(
                  dense: true,
                  leading: Text(c.flag, style: const TextStyle(fontSize: 20)),
                  title: Text(c.name, style: const TextStyle(fontSize: 13)),
                  trailing: Text('+${c.dial}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  onTap: () {
                    setState(() {
                      _country = c;
                      _countrySearch.text = '${c.name} (+${c.dial})';
                      _national = _national.replaceAll(RegExp(r'\D'), '').substring(
                            0,
                            _national.length.clamp(0, c.max),
                          );
                      _nationalCtrl.text = _national;
                    });
                    _syncEmit();
                  },
                );
              },
            ),
          ),
        const SizedBox(height: 8),
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
              decoration: BoxDecoration(
                color: Colors.teal.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.teal.shade200),
              ),
              child: Row(
                children: [
                  Text(_country.flag),
                  const SizedBox(width: 6),
                  Text('+${_country.dial}', style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: _nationalCtrl,
                keyboardType: TextInputType.phone,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: InputDecoration(
                  hintText: _country.min == _country.max
                      ? 'Numéro (${_country.min} chiffres)'
                      : 'Numéro (${_country.min}-${_country.max} chiffres)',
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
                onChanged: (v) {
                  _national = v.replaceAll(RegExp(r'\D'), '').substring(0, v.length.clamp(0, _country.max));
                  _nationalCtrl.value = TextEditingValue(
                    text: _national,
                    selection: TextSelection.collapsed(offset: _national.length),
                  );
                  _syncEmit();
                },
                onEditingComplete: widget.onBlur,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Indicatif actuel : +${_country.dial} (${_country.name}) — sans le 0 en tête du numéro local',
          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
        ),
        if (widget.error != null && widget.error!.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(widget.error!, style: const TextStyle(color: Colors.red, fontSize: 12)),
        ],
      ],
    );
  }
}

/// Téléphone mobile — FormField Flutter natif (même libellés que le web).
class SghlPhoneFormField extends FormField<String> {
  SghlPhoneFormField({
    super.key,
    required List<PhoneCountry> countries,
    String initialValue = '',
  }) : super(
          initialValue: initialValue,
          autovalidateMode: AutovalidateMode.onUserInteraction,
          validator: (v) {
            if (countries.isEmpty) return null;
            final msg = PhoneCountries.validateInternational(countries, v, required: true);
            return msg.isEmpty ? null : msg;
          },
          builder: (state) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                PhoneInput(
                  value: state.value ?? '',
                  required: true,
                  error: state.errorText,
                  onChanged: (v) => state.didChange(v),
                  onBlur: () => state.validate(),
                ),
              ],
            );
          },
        );
}

/// Champ téléphone mobile avec label identique au web (legacy).
class PhoneFormField extends StatelessWidget {
  final String label;
  final String? hint;
  final String value;
  final ValueChanged<String> onChanged;
  final String? error;
  final bool required;
  final VoidCallback? onBlur;

  const PhoneFormField({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.hint,
    this.error,
    this.required = false,
    this.onBlur,
  });

  @override
  Widget build(BuildContext context) {
    return AppFormField(
      label: label,
      hint: hint,
      error: null,
      required: required,
      child: PhoneInput(
        value: value,
        onChanged: onChanged,
        error: error,
        required: required,
        onBlur: onBlur,
      ),
    );
  }
}

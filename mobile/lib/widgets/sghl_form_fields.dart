import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Champ texte Flutter standard (TextFormField + InputDecoration).
class SghlTextFormField extends StatelessWidget {
  final TextEditingController controller;
  final String labelText;
  final String? hintText;
  final String? helperText;
  final bool required;
  final String? Function(String?)? validator;
  final TextInputType? keyboardType;
  final bool obscureText;
  final Iterable<String>? autofillHints;
  final List<TextInputFormatter>? inputFormatters;
  final TextInputAction? textInputAction;
  final void Function(String)? onFieldSubmitted;
  final int? maxLength;
  final TextAlign textAlign;
  final TextStyle? style;

  const SghlTextFormField({
    super.key,
    required this.controller,
    required this.labelText,
    this.hintText,
    this.helperText,
    this.required = false,
    this.validator,
    this.keyboardType,
    this.obscureText = false,
    this.autofillHints,
    this.inputFormatters,
    this.textInputAction,
    this.onFieldSubmitted,
    this.maxLength,
    this.textAlign = TextAlign.start,
    this.style,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscureText,
      autofillHints: autofillHints,
      inputFormatters: inputFormatters,
      textInputAction: textInputAction,
      onFieldSubmitted: onFieldSubmitted,
      maxLength: maxLength,
      textAlign: textAlign,
      style: style,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      validator: validator ??
          (required
              ? (v) {
                  if (v == null || v.trim().isEmpty) return '$labelText est obligatoire.';
                  return null;
                }
              : null),
      decoration: InputDecoration(
        labelText: required ? '$labelText *' : labelText,
        hintText: hintText,
        helperText: helperText,
      ),
    );
  }
}

/// Genre — DropdownButtonFormField intégré au Form.
class SghlGenderFormField extends StatelessWidget {
  final String value;
  final ValueChanged<String?> onChanged;

  const SghlGenderFormField({
    super.key,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      decoration: const InputDecoration(
        labelText: 'Genre *',
      ),
      items: const [
        DropdownMenuItem(value: 'F', child: Text('Féminin')),
        DropdownMenuItem(value: 'M', child: Text('Masculin')),
        DropdownMenuItem(value: 'O', child: Text('Autre')),
      ],
      onChanged: onChanged,
      validator: (v) => v == null || v.isEmpty ? 'Genre est obligatoire.' : null,
    );
  }
}

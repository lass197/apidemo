import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Thème SGHL Mobile — médical sobre (teal + ardoise).
class SghlTheme {
  static const Color teal = Color(0xFF0F766E);
  static const Color tealDark = Color(0xFF134E4A);
  static const Color slate = Color(0xFF1E293B);
  static const Color slateSoft = Color(0xFF334155);
  static const Color canvas = Color(0xFFF1F5F9);
  static const Color card = Color(0xFFFFFFFF);
  static const Color muted = Color(0xFF64748B);

  static const double radiusLg = 18;
  static const double radiusMd = 14;
  static const double radiusSm = 12;

  static List<BoxShadow> get softShadow => [
        BoxShadow(
          color: slate.withValues(alpha: 0.08),
          blurRadius: 24,
          offset: const Offset(0, 10),
        ),
      ];

  static BoxDecoration pageGradient({bool patient = true}) {
    return BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: patient
            ? const [Color(0xFFE8F5F3), Color(0xFFF1F5F9), Color(0xFFE2E8F0)]
            : const [Color(0xFFE6F4F1), Color(0xFFF1F5F9), Color(0xFFE2E8F0)],
      ),
    );
  }

  static BoxDecoration headerGradient({bool doctor = false}) {
    return BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: doctor
            ? const [tealDark, teal]
            : const [slate, slateSoft],
      ),
    );
  }

  static TextStyle sectionTitle(BuildContext context) {
    return Theme.of(context).textTheme.titleMedium!.copyWith(
          fontWeight: FontWeight.w700,
          color: slate,
        );
  }

  static ThemeData light() {
    final base = GoogleFonts.plusJakartaSansTextTheme();
    final scheme = ColorScheme.fromSeed(
      seedColor: teal,
      primary: teal,
      secondary: slate,
      surface: card,
      brightness: Brightness.light,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: canvas,
      textTheme: base.apply(bodyColor: slate, displayColor: slate),
      appBarTheme: AppBarTheme(
        elevation: 0,
        centerTitle: false,
        backgroundColor: slate,
        foregroundColor: Colors.white,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: Colors.white,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusMd),
          side: BorderSide(color: Colors.black.withValues(alpha: 0.06)),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(radiusSm)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: BorderSide(color: Colors.black.withValues(alpha: 0.1)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusSm),
          borderSide: const BorderSide(color: teal, width: 1.5),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: teal,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusSm)),
          textStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600, fontSize: 15),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: slate,
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusSm)),
          side: BorderSide(color: Colors.black.withValues(alpha: 0.12)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        elevation: 0,
        height: 68,
        indicatorColor: teal.withValues(alpha: 0.14),
        labelTextStyle: WidgetStatePropertyAll(
          GoogleFonts.plusJakartaSans(fontSize: 12, fontWeight: FontWeight.w600),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: teal.withValues(alpha: 0.1),
        labelStyle: GoogleFonts.plusJakartaSans(fontSize: 11, fontWeight: FontWeight.w600, color: tealDark),
        side: BorderSide.none,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}

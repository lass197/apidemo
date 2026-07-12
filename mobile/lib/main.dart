import 'package:flutter/material.dart';

import 'screens/doctor_home_screen.dart';
import 'screens/patient_home_screen.dart';
import 'screens/portal_screen.dart';
import 'services/auth_service.dart';
import 'services/token_storage.dart';
import 'theme/sghl_theme.dart';
import 'widgets/sghl_ui.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await TokenStorage.init();
  runApp(const SghlApp());
}

class SghlApp extends StatelessWidget {
  const SghlApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SGHL',
      debugShowCheckedModeBanner: false,
      theme: SghlTheme.light(),
      home: const _BootstrapScreen(),
    );
  }
}

class _BootstrapScreen extends StatelessWidget {
  const _BootstrapScreen();

  Future<Widget> _resolveHome() async {
    final loggedIn = await AuthService.isLoggedIn();
    if (!loggedIn) return const PortalScreen();

    final portal = await AuthService.resolvePortal();
    if (portal == PortalType.doctor) return const DoctorHomeScreen();
    if (portal == PortalType.patient) return const PatientHomeScreen();

    await AuthService.logout();
    return const PortalScreen();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Widget>(
      future: _resolveHome(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return Scaffold(
            body: Container(
              decoration: SghlTheme.pageGradient(),
              child: const SghlLoading(message: 'Chargement…'),
            ),
          );
        }
        return snapshot.data ?? const PortalScreen();
      },
    );
  }
}

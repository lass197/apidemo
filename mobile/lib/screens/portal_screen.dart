import 'package:flutter/material.dart';

import '../services/auth_service.dart';
import '../theme/sghl_theme.dart';
import 'login_screen.dart';

class PortalScreen extends StatelessWidget {
  const PortalScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFE8F5F3), Color(0xFFF1F5F9), Color(0xFFE2E8F0)],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 720;
              return Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 880),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: 24),
                        Text(
                          'SGHL',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 48,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -1.5,
                            color: SghlTheme.slate,
                            height: 1,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          'Hôpital de Dolisie',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 16,
                            color: SghlTheme.muted,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Choisissez votre espace',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                        ),
                        const SizedBox(height: 40),
                        if (wide)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(child: _portalCard(context, PortalType.patient)),
                              const SizedBox(width: 20),
                              Expanded(child: _portalCard(context, PortalType.doctor)),
                            ],
                          )
                        else ...[
                          _portalCard(context, PortalType.patient),
                          const SizedBox(height: 16),
                          _portalCard(context, PortalType.doctor),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _portalCard(BuildContext context, PortalType portal) {
    if (portal == PortalType.patient) {
      return _PortalCard(
        icon: Icons.person_rounded,
        title: 'Espace patient',
        subtitle: 'Rendez-vous, résultats, soins et messagerie',
        demo: 'alice.moreau / Patient@2026',
        colors: const [Color(0xFF1E293B), Color(0xFF334155)],
        onTap: () => _openLogin(context, portal),
      );
    }
    return _PortalCard(
      icon: Icons.medical_services_rounded,
      title: 'Espace médecin',
      subtitle: 'Agenda, patients et messagerie clinique',
      demo: 'dr.martin / Medecin@2026',
      colors: const [SghlTheme.tealDark, SghlTheme.teal],
      onTap: () => _openLogin(context, portal),
    );
  }

  void _openLogin(BuildContext context, PortalType portal) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => LoginScreen(portal: portal)),
    );
  }
}

class _PortalCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String demo;
  final List<Color> colors;
  final VoidCallback onTap;

  const _PortalCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.demo,
    required this.colors,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: LinearGradient(
              colors: colors,
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            boxShadow: [
              BoxShadow(
                color: colors.first.withValues(alpha: 0.28),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: Colors.white, size: 32),
                ),
                const SizedBox(height: 20),
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 14, height: 1.4),
                ),
                const SizedBox(height: 20),
                Text(
                  demo,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Text(
                      'Accéder',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.95),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Icon(Icons.arrow_forward_rounded, color: Colors.white.withValues(alpha: 0.95), size: 18),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

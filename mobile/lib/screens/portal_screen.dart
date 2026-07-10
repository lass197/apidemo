import 'package:flutter/material.dart';

import '../services/auth_service.dart';
import 'login_screen.dart';

class PortalScreen extends StatelessWidget {
  const PortalScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth >= 720;
            return Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: 900),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const SizedBox(height: 16),
                      const Icon(Icons.local_hospital_rounded, size: 72, color: Color(0xFF0D9488)),
                      const SizedBox(height: 16),
                      const Text(
                        'SGHL Mobile',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Hôpital de Dolisie — choisissez votre espace',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 15),
                      ),
                      const SizedBox(height: 32),
                      if (wide)
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(child: _portalCard(context, PortalType.patient)),
                            const SizedBox(width: 16),
                            Expanded(child: _portalCard(context, PortalType.doctor)),
                          ],
                        )
                      else ...[
                        _portalCard(context, PortalType.patient),
                        const SizedBox(height: 16),
                        _portalCard(context, PortalType.doctor),
                      ],
                      const SizedBox(height: 24),
                      Text(
                        'Compatible Chrome (web) et téléphone Android',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _portalCard(BuildContext context, PortalType portal) {
    if (portal == PortalType.patient) {
      return _PortalCard(
        icon: '👤',
        title: 'Espace patient',
        subtitle: 'Rendez-vous, résultats, soins, messagerie et rappels',
        demo: 'alice.moreau / Patient@2026',
        gradient: const [Color(0xFF475569), Color(0xFF1E293B)],
        onTap: () => _openLogin(context, portal),
      );
    }
    return _PortalCard(
      icon: '🩺',
      title: 'Espace médecin',
      subtitle: 'Mes rendez-vous, patients et messagerie',
      demo: 'dr.martin / Medecin@2026',
      gradient: const [Color(0xFF0D9488), Color(0xFF134E4A)],
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
  final String icon;
  final String title;
  final String subtitle;
  final String demo;
  final List<Color> gradient;
  final VoidCallback onTap;

  const _PortalCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.demo,
    required this.gradient,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(colors: gradient, begin: Alignment.topLeft, end: Alignment.bottomRight),
            boxShadow: [
              BoxShadow(
                color: gradient.first.withValues(alpha: 0.35),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(icon, style: const TextStyle(fontSize: 40)),
                const SizedBox(height: 16),
                Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(subtitle, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 14)),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    demo,
                    style: const TextStyle(color: Colors.white, fontSize: 11, fontFamily: 'monospace'),
                  ),
                ),
                const SizedBox(height: 16),
                const Row(
                  children: [
                    Text('Accéder', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                    SizedBox(width: 6),
                    Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 18),
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

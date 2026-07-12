import 'package:flutter/material.dart';

import '../services/auth_service.dart';
import '../theme/sghl_theme.dart';
import 'login_screen.dart';

class PortalScreen extends StatefulWidget {
  const PortalScreen({super.key});

  @override
  State<PortalScreen> createState() => _PortalScreenState();
}

class _PortalScreenState extends State<PortalScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _fade;
  late final Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));
    _fade = CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic);
    _slide = Tween<Offset>(begin: const Offset(0, 0.06), end: Offset.zero).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic),
    );
    _ctrl.forward();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: SghlTheme.pageGradient(),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 720;
              return Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 880),
                    child: FadeTransition(
                      opacity: _fade,
                      child: SlideTransition(
                        position: _slide,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const SizedBox(height: 20),
                            Center(
                              child: Container(
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: SghlTheme.teal.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(22),
                                ),
                                child: const Icon(
                                  Icons.local_hospital_rounded,
                                  size: 40,
                                  color: SghlTheme.teal,
                                ),
                              ),
                            ),
                            const SizedBox(height: 20),
                            const Text(
                              'SGHL',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 52,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -1.8,
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
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 6),
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
                                  Expanded(child: _portalCard(context, PortalType.patient, 0)),
                                  const SizedBox(width: 20),
                                  Expanded(child: _portalCard(context, PortalType.doctor, 1)),
                                ],
                              )
                            else ...[
                              _portalCard(context, PortalType.patient, 0),
                              const SizedBox(height: 16),
                              _portalCard(context, PortalType.doctor, 1),
                            ],
                          ],
                        ),
                      ),
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

  Widget _portalCard(BuildContext context, PortalType portal, int index) {
    final delay = (120 + index * 90) / 700;
    return FadeTransition(
      opacity: CurvedAnimation(
        parent: _ctrl,
        curve: Interval(delay.clamp(0.0, 0.85), 1.0, curve: Curves.easeOut),
      ),
      child: portal == PortalType.patient
          ? _PortalCard(
              icon: Icons.person_rounded,
              title: 'Espace patient',
              subtitle: 'Rendez-vous, résultats, soins et messagerie',
              hint: 'Compte démo disponible',
              colors: const [Color(0xFF1E293B), Color(0xFF334155)],
              onTap: () => _openLogin(context, portal),
            )
          : _PortalCard(
              icon: Icons.medical_services_rounded,
              title: 'Espace médecin',
              subtitle: 'Agenda, patients et messagerie clinique',
              hint: 'Accès personnel hospitalier',
              colors: const [SghlTheme.tealDark, SghlTheme.teal],
              onTap: () => _openLogin(context, portal),
            ),
    );
  }

  void _openLogin(BuildContext context, PortalType portal) {
    Navigator.push(
      context,
      PageRouteBuilder(
        pageBuilder: (_, a, __) => LoginScreen(portal: portal),
        transitionsBuilder: (_, a, __, child) {
          return FadeTransition(
            opacity: a,
            child: SlideTransition(
              position: Tween<Offset>(begin: const Offset(0.04, 0), end: Offset.zero).animate(
                CurvedAnimation(parent: a, curve: Curves.easeOutCubic),
              ),
              child: child,
            ),
          );
        },
        transitionDuration: const Duration(milliseconds: 320),
      ),
    );
  }
}

class _PortalCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String hint;
  final List<Color> colors;
  final VoidCallback onTap;

  const _PortalCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.hint,
    required this.colors,
    required this.onTap,
  });

  @override
  State<_PortalCard> createState() => _PortalCardState();
}

class _PortalCardState extends State<_PortalCard> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return AnimatedScale(
      scale: _pressed ? 0.97 : 1,
      duration: const Duration(milliseconds: 120),
      curve: Curves.easeOut,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: widget.onTap,
          onHighlightChanged: (v) => setState(() => _pressed = v),
          borderRadius: BorderRadius.circular(SghlTheme.radiusLg),
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(SghlTheme.radiusLg),
              gradient: LinearGradient(
                colors: widget.colors,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              boxShadow: [
                BoxShadow(
                  color: widget.colors.first.withValues(alpha: 0.3),
                  blurRadius: 22,
                  offset: const Offset(0, 12),
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
                    child: Icon(widget.icon, color: Colors.white, size: 32),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    widget.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.subtitle,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 14,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    widget.hint,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.55),
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Text(
                        'Accéder',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.95),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.arrow_forward_rounded,
                        color: Colors.white.withValues(alpha: 0.95),
                        size: 18,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

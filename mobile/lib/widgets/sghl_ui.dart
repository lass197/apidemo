import 'package:flutter/material.dart';

import '../theme/sghl_theme.dart';

/// Indicateur de chargement unifié.
class SghlLoading extends StatelessWidget {
  final String? message;

  const SghlLoading({super.key, this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 36,
            height: 36,
            child: CircularProgressIndicator(strokeWidth: 3, color: SghlTheme.teal),
          ),
          if (message != null) ...[
            const SizedBox(height: 14),
            Text(message!, style: TextStyle(color: SghlTheme.muted, fontSize: 13)),
          ],
        ],
      ),
    );
  }
}

/// État vide unifié.
class SghlEmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;

  const SghlEmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: SghlTheme.teal.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Icon(icon, size: 36, color: SghlTheme.teal),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: SghlTheme.slate,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(
                subtitle!,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: SghlTheme.muted, height: 1.4),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Carte liste uniforme (RDV, patients, factures…).
class SghlListTileCard extends StatelessWidget {
  final Widget? leading;
  final Widget title;
  final Widget? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry margin;

  const SghlListTileCard({
    super.key,
    this.leading,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.margin = const EdgeInsets.only(bottom: 10),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(SghlTheme.radiusMd),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        boxShadow: [
          BoxShadow(
            color: SghlTheme.slate.withValues(alpha: 0.04),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(SghlTheme.radiusMd),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (leading != null) ...[leading!, const SizedBox(width: 12)],
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DefaultTextStyle.merge(
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                          color: SghlTheme.slate,
                        ),
                        child: title,
                      ),
                      if (subtitle != null) ...[
                        const SizedBox(height: 4),
                        DefaultTextStyle.merge(
                          style: TextStyle(fontSize: 13, color: SghlTheme.muted, height: 1.35),
                          child: subtitle!,
                        ),
                      ],
                    ],
                  ),
                ),
                if (trailing != null) ...[const SizedBox(width: 8), trailing!],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Panneau formulaire blanc avec ombre douce.
class SghlFormPanel extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const SghlFormPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(24),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(SghlTheme.radiusLg),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        boxShadow: SghlTheme.softShadow,
      ),
      child: Padding(padding: padding, child: child),
    );
  }
}

/// Badge statut discret.
class SghlStatusBadge extends StatelessWidget {
  final String label;
  final Color? color;

  const SghlStatusBadge({super.key, required this.label, this.color});

  @override
  Widget build(BuildContext context) {
    final c = color ?? SghlTheme.teal;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c),
      ),
    );
  }
}

/// En-tête auth (login / register) avec dégradé.
class SghlAuthHeader extends StatelessWidget {
  final bool doctor;
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback? onBack;

  const SghlAuthHeader({
    super.key,
    this.doctor = false,
    required this.title,
    required this.subtitle,
    required this.icon,
    this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.only(
        top: MediaQuery.paddingOf(context).top + 8,
        left: 8,
        right: 24,
        bottom: 32,
      ),
      decoration: SghlTheme.headerGradient(doctor: doctor),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (onBack != null)
            IconButton(
              onPressed: onBack,
              icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
            ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: Colors.white, size: 28),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'SGHL',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.75),
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.8),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../icons/lucide_adapter.dart' as lucide;
import '../../l10n/app_localizations.dart';

class DesktopAboutPane extends StatefulWidget {
  const DesktopAboutPane({super.key});

  @override
  State<DesktopAboutPane> createState() => _DesktopAboutPaneState();
}

class _DesktopAboutPaneState extends State<DesktopAboutPane> {
  String _version = '';

  @override
  void initState() {
    super.initState();
    _loadInfo();
  }

  Future<void> _loadInfo() async {
    try {
      final pkg = await PackageInfo.fromPlatform();
      if (!mounted) return;
      setState(() {
        _version = pkg.version;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _version = '-';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final l10n = AppLocalizations.of(context)!;

    return Container(
      alignment: Alignment.topCenter,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                height: 36,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    l10n.settingsPageAbout,
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w400, color: cs.onSurface.withOpacity(0.9)),
                  ),
                ),
              ),
              const SizedBox(height: 8),

              // App info
              _DeskCard(
                title: l10n.settingsPageAbout,
                children: [
                  _DeskInfoRow(
                    icon: lucide.Lucide.Phone,
                    label: 'App Name',
                    detail: 'Build X',
                  ),
                  const _DeskRowDivider(),
                  _DeskInfoRow(
                    icon: lucide.Lucide.Code,
                    label: l10n.aboutPageVersion,
                    detail: _version.isEmpty ? '...' : _version,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AppHeaderCard extends StatefulWidget {
  const _AppHeaderCard({required this.description});
  final String description;
  @override
  State<_AppHeaderCard> createState() => _AppHeaderCardState();
}

class _AppHeaderCardState extends State<_AppHeaderCard> {
  bool _hover = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseBg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final hoverBg = isDark ? Colors.white.withOpacity(0.06) : Colors.black.withOpacity(0.04);
    final overlay = _hover ? hoverBg : Colors.transparent;
    return MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => setState(() => _pressed = true),
        onTapUp: (_) => setState(() => _pressed = false),
        onTapCancel: () => setState(() => _pressed = false),
        onTap: () {},
        child: AnimatedScale(
          scale: _pressed ? 0.995 : 1.0,
          duration: const Duration(milliseconds: 110),
          curve: Curves.easeOutCubic,
          child: DecoratedBox(
            decoration: ShapeDecoration(
              color: Color.alphaBlend(overlay, baseBg),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(
                  width: 0.5,
                  color: isDark ? Colors.white.withOpacity(0.06) : cs.outlineVariant.withOpacity(0.12),
                ),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: SizedBox(
                      width: 54,
                      height: 54,
                      child: Image.asset('assets/app_icon.png', fit: BoxFit.cover),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text('Build X', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        Text(
                          widget.description,
                          style: TextStyle(fontSize: 13, color: cs.onSurface.withOpacity(0.65), height: 1.2),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
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

class _DeskCard extends StatelessWidget {
  const _DeskCard({required this.title, required this.children});
  final String title;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Material(
      color: isDark ? const Color(0xFF1C1C1E) : Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(width: 0.5, color: isDark ? Colors.white.withOpacity(0.06) : cs.outlineVariant.withOpacity(0.12)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 2, 4, 8),
              child: Text(title, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: cs.onSurface)),
            ),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _DeskRowDivider extends StatelessWidget {
  const _DeskRowDivider();
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Divider(height: 1, thickness: 0.5, indent: 8, endIndent: 8, color: cs.outlineVariant.withOpacity(0.12)),
    );
  }
}

class _DeskInfoRow extends StatelessWidget {
  const _DeskInfoRow({required this.icon, required this.label, required this.detail});
  final IconData icon;
  final String label;
  final String detail;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          SizedBox(width: 26, child: Icon(icon, size: 18, color: cs.onSurface.withOpacity(0.9))),
          const SizedBox(width: 10),
          Expanded(
            child: Text(label, style: TextStyle(fontSize: 14.5, color: cs.onSurface.withOpacity(0.92))),
          ),
          const SizedBox(width: 10),
          Text(detail, style: TextStyle(fontSize: 13, color: cs.onSurface.withOpacity(0.6))),
        ],
      ),
    );
  }
}




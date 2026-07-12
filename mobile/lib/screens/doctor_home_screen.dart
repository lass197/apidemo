import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/auth_service.dart';
import '../theme/sghl_theme.dart';
import '../widgets/sghl_ui.dart';
import 'portal_screen.dart';

class DoctorHomeScreen extends StatefulWidget {
  const DoctorHomeScreen({super.key});

  @override
  State<DoctorHomeScreen> createState() => _DoctorHomeScreenState();
}

class _DoctorHomeScreenState extends State<DoctorHomeScreen> {
  int _index = 0;
  Map<String, dynamic>? _user;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    final u = await AuthService.getUser();
    if (mounted) setState(() => _user = u);
  }

  Future<void> _logout() async {
    await AuthService.logout();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const PortalScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final name = _user != null ? '${_user!['first_name']} ${_user!['last_name']}' : 'Médecin';
    return Scaffold(
      backgroundColor: SghlTheme.canvas,
      appBar: AppBar(
        backgroundColor: SghlTheme.tealDark,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'SGHL',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Colors.white70),
            ),
            Text(
              'Dr. $name',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.logout_rounded), tooltip: 'Déconnexion', onPressed: _logout),
        ],
      ),
      body: IndexedStack(
        index: _index,
        children: const [
          DoctorAppointmentsTab(),
          DoctorPatientsTab(),
          DoctorChatTab(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.event_outlined), selectedIcon: Icon(Icons.event), label: 'RDV'),
          NavigationDestination(icon: Icon(Icons.people_outline), selectedIcon: Icon(Icons.people), label: 'Patients'),
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), selectedIcon: Icon(Icons.chat_bubble), label: 'Messages'),
        ],
      ),
    );
  }
}

String _fmtDate(String? iso) {
  if (iso == null) return '—';
  try {
    return DateFormat('EEE d MMM yyyy · HH:mm', 'fr_FR').format(DateTime.parse(iso).toLocal());
  } catch (_) {
    return iso;
  }
}

const _statusLabels = {
  'PENDING': 'En attente',
  'CONFIRMED': 'Confirmé',
  'CANCELLED': 'Annulé',
  'COMPLETED': 'Terminé',
};

Color _statusColor(String status) {
  switch (status) {
    case 'CONFIRMED':
      return SghlTheme.teal;
    case 'CANCELLED':
      return const Color(0xFFB91C1C);
    case 'COMPLETED':
      return const Color(0xFF475569);
    default:
      return const Color(0xFFCA8A04);
  }
}

class DoctorAppointmentsTab extends StatefulWidget {
  const DoctorAppointmentsTab({super.key});

  @override
  State<DoctorAppointmentsTab> createState() => _DoctorAppointmentsTabState();
}

class _DoctorAppointmentsTabState extends State<DoctorAppointmentsTab> {
  List<dynamic> _appointments = [];
  bool _loading = true;
  String _filter = 'upcoming';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final appts = await ApiService.getDoctorAppointments();
    if (mounted) {
      setState(() {
        _appointments = appts;
        _loading = false;
      });
    }
  }

  List<dynamic> get _filtered {
    final now = DateTime.now();
    if (_filter == 'upcoming') {
      return _appointments.where((a) {
        final status = a['status'] as String? ?? '';
        if (!['PENDING', 'CONFIRMED'].contains(status)) return false;
        try {
          return DateTime.parse(a['scheduled_at'] as String).isAfter(now);
        } catch (_) {
          return true;
        }
      }).toList();
    }
    return _appointments;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const SghlLoading();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'upcoming', label: Text('À venir')),
              ButtonSegment(value: 'all', label: Text('Tous')),
            ],
            selected: {_filter},
            onSelectionChanged: (s) => setState(() => _filter = s.first),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: _filtered.isEmpty
                ? ListView(
                    children: const [
                      SizedBox(height: 80),
                      SghlEmptyState(
                        icon: Icons.event_busy_outlined,
                        title: 'Aucun rendez-vous',
                        subtitle: 'Les rendez-vous à venir apparaîtront ici.',
                      ),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _filtered.length,
                    itemBuilder: (_, i) {
                      final a = _filtered[i];
                      final status = a['status'] as String? ?? '';
                      return SghlListTileCard(
                        leading: CircleAvatar(
                          backgroundColor: SghlTheme.teal.withValues(alpha: 0.12),
                          child: const Icon(Icons.person, color: SghlTheme.teal),
                        ),
                        title: Text(a['patient_name'] as String? ?? 'Patient'),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(_fmtDate(a['scheduled_at'] as String?)),
                            if ((a['patient_phone'] as String?)?.isNotEmpty == true)
                              Text(a['patient_phone'] as String),
                            if ((a['patient_email'] as String?)?.isNotEmpty == true)
                              Text(a['patient_email'] as String),
                          ],
                        ),
                        trailing: SghlStatusBadge(
                          label: _statusLabels[status] ?? status,
                          color: _statusColor(status),
                        ),
                      );
                    },
                  ),
          ),
        ),
      ],
    );
  }
}

class DoctorPatientsTab extends StatefulWidget {
  const DoctorPatientsTab({super.key});

  @override
  State<DoctorPatientsTab> createState() => _DoctorPatientsTabState();
}

class _DoctorPatientsTabState extends State<DoctorPatientsTab> {
  List<dynamic> _patients = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final pats = await ApiService.getDoctorPatients();
    if (mounted) {
      setState(() {
        _patients = pats;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const SghlLoading();

    return RefreshIndicator(
      onRefresh: _load,
      child: _patients.isEmpty
          ? ListView(
              children: const [
                SizedBox(height: 80),
                SghlEmptyState(
                  icon: Icons.people_outline,
                  title: 'Aucun patient',
                ),
              ],
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _patients.length,
              itemBuilder: (_, i) {
                final p = _patients[i];
                final name = p['name'] as String? ?? 'Patient';
                return SghlListTileCard(
                  leading: CircleAvatar(
                    backgroundColor: SghlTheme.teal.withValues(alpha: 0.1),
                    child: Text(
                      name.isNotEmpty ? name.substring(0, 1).toUpperCase() : 'P',
                      style: const TextStyle(color: SghlTheme.teal, fontWeight: FontWeight.bold),
                    ),
                  ),
                  title: Text(name),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if ((p['phone'] as String?)?.isNotEmpty == true) Text(p['phone'] as String),
                      if ((p['email'] as String?)?.isNotEmpty == true) Text(p['email'] as String),
                      Text(
                        p['next_appointment_at'] != null
                            ? 'Prochain RDV : ${_fmtDate(p['next_appointment_at'] as String?)}'
                            : 'Pas de RDV à venir',
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}

class DoctorChatTab extends StatefulWidget {
  const DoctorChatTab({super.key});

  @override
  State<DoctorChatTab> createState() => _DoctorChatTabState();
}

class _DoctorChatTabState extends State<DoctorChatTab> {
  List<dynamic> _patients = [];
  String? _selectedPatientId;
  List<dynamic> _messages = [];
  final _ctrl = TextEditingController();
  bool _loadingPatients = true;

  @override
  void initState() {
    super.initState();
    _loadPatients();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _loadPatients() async {
    setState(() => _loadingPatients = true);
    final pats = await ApiService.getDoctorPatients();
    if (mounted) {
      setState(() {
        _patients = pats;
        _selectedPatientId ??= pats.isNotEmpty ? pats.first['id'] as String : null;
        _loadingPatients = false;
      });
      if (_selectedPatientId != null) await _loadMessages();
    }
  }

  Future<void> _loadMessages() async {
    if (_selectedPatientId == null) return;
    final msgs = await ApiService.getChat(_selectedPatientId!);
    if (mounted) setState(() => _messages = msgs);
  }

  Future<void> _send() async {
    if (_selectedPatientId == null || _ctrl.text.trim().isEmpty) return;
    await ApiService.sendChat(_selectedPatientId!, _ctrl.text.trim());
    _ctrl.clear();
    await _loadMessages();
  }

  @override
  Widget build(BuildContext context) {
    if (_loadingPatients) return const SghlLoading();
    if (_patients.isEmpty) {
      return const SghlEmptyState(
        icon: Icons.chat_bubble_outline,
        title: 'Aucun patient pour la messagerie',
      );
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: DropdownButtonFormField<String>(
            value: _selectedPatientId,
            decoration: const InputDecoration(
              labelText: 'Patient',
              isDense: true,
            ),
            items: _patients
                .map((p) => DropdownMenuItem(
                      value: p['id'] as String,
                      child: Text(p['name'] as String? ?? 'Patient'),
                    ))
                .toList(),
            onChanged: (v) async {
              setState(() => _selectedPatientId = v);
              await _loadMessages();
            },
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            itemCount: _messages.length,
            itemBuilder: (_, i) {
              final m = _messages[i];
              return Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: SghlTheme.teal.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: SghlTheme.teal.withValues(alpha: 0.15)),
                  ),
                  child: Text(m['content'] as String? ?? ''),
                ),
              );
            },
          ),
        ),
        Material(
          elevation: 4,
          color: Colors.white,
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _ctrl,
                    decoration: const InputDecoration(
                      hintText: 'Répondre au patient…',
                      contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                    onSubmitted: (_) => _send(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(onPressed: _send, icon: const Icon(Icons.send_rounded)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

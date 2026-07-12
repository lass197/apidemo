import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/auth_service.dart';
import '../theme/sghl_theme.dart';
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
    if (_loading) return const Center(child: CircularProgressIndicator());

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
                ? ListView(children: const [SizedBox(height: 120), Center(child: Text('Aucun rendez-vous'))])
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _filtered.length,
                    itemBuilder: (_, i) {
                      final a = _filtered[i];
                      final status = a['status'] as String? ?? '';
                      return Card(
                        elevation: 0,
                        margin: const EdgeInsets.only(bottom: 10),
                        child: ListTile(
                          isThreeLine: true,
                          leading: CircleAvatar(
                            backgroundColor: Colors.teal.shade100,
                            child: const Icon(Icons.person, color: Colors.teal),
                          ),
                          title: Text(a['patient_name'] as String? ?? 'Patient', style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_fmtDate(a['scheduled_at'] as String?)),
                              if ((a['patient_phone'] as String?)?.isNotEmpty == true)
                                Text('📞 ${a['patient_phone']}', style: const TextStyle(fontSize: 12)),
                              if ((a['patient_email'] as String?)?.isNotEmpty == true)
                                Text('✉ ${a['patient_email']}', style: const TextStyle(fontSize: 12)),
                            ],
                          ),
                          trailing: Chip(
                            label: Text(_statusLabels[status] ?? status, style: const TextStyle(fontSize: 10)),
                          ),
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
    if (_loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: _load,
      child: _patients.isEmpty
          ? ListView(children: const [SizedBox(height: 120), Center(child: Text('Aucun patient'))])
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _patients.length,
              itemBuilder: (_, i) {
                final p = _patients[i];
                return Card(
                  elevation: 0,
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Colors.teal.shade50,
                      child: Text(
                        (p['name'] as String? ?? 'P').substring(0, 1).toUpperCase(),
                        style: const TextStyle(color: Color(0xFF0D9488), fontWeight: FontWeight.bold),
                      ),
                    ),
                    title: Text(p['name'] as String? ?? 'Patient', style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if ((p['phone'] as String?)?.isNotEmpty == true) Text('📞 ${p['phone']}'),
                        if ((p['email'] as String?)?.isNotEmpty == true) Text('✉ ${p['email']}'),
                        Text(
                          p['next_appointment_at'] != null
                              ? 'Prochain RDV : ${_fmtDate(p['next_appointment_at'] as String?)}'
                              : 'Pas de RDV à venir',
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                    isThreeLine: true,
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
    if (_loadingPatients) return const Center(child: CircularProgressIndicator());
    if (_patients.isEmpty) {
      return const Center(child: Text('Aucun patient pour la messagerie'));
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: DropdownButtonFormField<String>(
            value: _selectedPatientId,
            decoration: const InputDecoration(
              labelText: 'Patient',
              border: OutlineInputBorder(),
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
                    color: Colors.teal.shade50,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.teal.shade100),
                  ),
                  child: Text(m['content'] as String? ?? ''),
                ),
              );
            },
          ),
        ),
        Material(
          elevation: 8,
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _ctrl,
                    decoration: const InputDecoration(
                      hintText: 'Répondre au patient…',
                      border: OutlineInputBorder(),
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

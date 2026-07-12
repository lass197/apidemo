import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/auth_service.dart';
import '../theme/sghl_theme.dart';
import '../utils/document_save.dart';
import 'portal_screen.dart';

class PatientHomeScreen extends StatefulWidget {
  const PatientHomeScreen({super.key});

  @override
  State<PatientHomeScreen> createState() => _PatientHomeScreenState();
}

class _PatientHomeScreenState extends State<PatientHomeScreen> {
  int _index = 0;
  Map<String, dynamic>? _patient;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    final p = await ApiService.getPatientProfile();
    if (mounted) setState(() => _patient = p);
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
    if (_patient == null) {
      return Scaffold(
        backgroundColor: SghlTheme.canvas,
        appBar: AppBar(
          title: const Text('SGHL'),
        ),
        body: const Center(child: CircularProgressIndicator(color: SghlTheme.teal)),
      );
    }

    final patientId = _patient!['id'].toString();
    return Scaffold(
      backgroundColor: SghlTheme.canvas,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'SGHL',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Colors.white70),
            ),
            Text(
              'Bonjour, ${_patient!['first_name']}',
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
        children: [
          RdvTab(patientId: patientId),
          InvoicesTab(patientPhone: _patient!['phone'] as String? ?? ''),
          DossierTab(patientId: patientId, patient: _patient!),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month), label: 'RDV'),
          NavigationDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: 'Factures'),
          NavigationDestination(icon: Icon(Icons.folder_shared_outlined), selectedIcon: Icon(Icons.folder_shared), label: 'Dossier'),
        ],
      ),
    );
  }
}

class RdvTab extends StatefulWidget {
  final String patientId;
  const RdvTab({super.key, required this.patientId});

  @override
  State<RdvTab> createState() => _RdvTabState();
}

class _RdvTabState extends State<RdvTab> {
  List<dynamic> _appointments = [];
  List<dynamic> _doctors = [];
  List<dynamic> _services = [];
  List<dynamic> _slots = [];
  String? _doctorId;
  String? _serviceId;
  String? _selectedSlot;
  final _reasonCtrl = TextEditingController();
  bool _loading = true;

  Map<String, dynamic>? get _selectedService {
    if (_serviceId == null) return null;
    for (final s in _services) {
      if (s['id'] == _serviceId) return s as Map<String, dynamic>;
    }
    return null;
  }

  void _applyServiceDoctorHint() {
    final service = _selectedService;
    if (service == null) return;
    final code = (service['code'] as String?) ?? '';
    final dept = (service['department_code'] as String?) ?? '';
    if (code == 'PED' || dept == 'PEDIA') {
      for (final d in _doctors) {
        final specialty = (d['specialty'] as String?)?.toLowerCase() ?? '';
        if (specialty.contains('pédiatrie')) {
          _doctorId = d['id'] as String?;
          break;
        }
      }
    }
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _reasonCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final appts = await ApiService.getMyPatientAppointments();
    final docs = await ApiService.getDoctors();
    final svcs = await ApiService.getHospitalServices();
    if (mounted) {
      setState(() {
        _appointments = appts;
        _doctors = docs;
        _services = svcs;
        _doctorId ??= docs.isNotEmpty ? docs.first['id'] as String : null;
        _loading = false;
      });
      if (_doctorId != null) await _loadSlots();
    }
  }

  Future<void> _loadSlots() async {
    if (_doctorId == null) return;
    final slots = await ApiService.getAvailableSlots(_doctorId!);
    if (mounted) {
      setState(() {
        _slots = slots.where((s) => s['available'] == true).toList();
        _selectedSlot = _slots.isNotEmpty ? _slots.first['scheduled_at'] as String : null;
      });
    }
  }

  Future<void> _book() async {
    if (widget.patientId.isEmpty || _doctorId == null || _selectedSlot == null) return;
    final ok = await ApiService.bookAppointment(
      patientId: widget.patientId,
      doctorId: _doctorId!,
      scheduledAt: _selectedSlot!,
      reason: _reasonCtrl.text,
      serviceId: _serviceId,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? 'Rendez-vous confirmé' : 'Créneau indisponible'),
        behavior: SnackBarBehavior.floating,
      ),
    );
    await _load();
  }

  String _fmt(String? iso) {
    if (iso == null) return '';
    try {
      return DateFormat('EEE d MMM yyyy · HH:mm', 'fr_FR').format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }

  String _statusLabel(String? status) {
    switch (status) {
      case 'PENDING':
        return 'En attente';
      case 'CONFIRMED':
        return 'Confirmé';
      case 'CANCELLED':
        return 'Annulé';
      case 'COMPLETED':
        return 'Terminé';
      default:
        return status ?? '';
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.patientId.isEmpty) {
      return const Center(child: Text('Profil patient non lié au compte.'));
    }
    if (_loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: Colors.grey.shade200),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Nouveau rendez-vous', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 12),
                  if (_services.isNotEmpty)
                    DropdownButtonFormField<String>(
                      value: _serviceId,
                      decoration: const InputDecoration(labelText: 'Prestation (optionnel)', border: OutlineInputBorder()),
                      items: [
                        const DropdownMenuItem<String>(value: null, child: Text('— Choisir —')),
                        ..._services.map(
                          (s) => DropdownMenuItem(
                            value: s['id'] as String,
                            child: Text('${s['icon'] ?? '🏥'} ${s['name']}'),
                          ),
                        ),
                      ],
                      onChanged: (v) async {
                        setState(() => _serviceId = v);
                        _applyServiceDoctorHint();
                        await _loadSlots();
                      },
                    ),
                  if (_selectedService != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.teal.shade50,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.teal.shade100),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _selectedService!['description'] as String? ?? '',
                            style: TextStyle(fontSize: 13, color: Colors.grey.shade800),
                          ),
                          if ((_selectedService!['location_hint'] as String?)?.isNotEmpty == true) ...[
                            const SizedBox(height: 6),
                            Text(
                              '📍 ${_selectedService!['location_hint']}',
                              style: TextStyle(fontSize: 12, color: Colors.teal.shade800),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _doctorId,
                    decoration: const InputDecoration(labelText: 'Médecin', border: OutlineInputBorder()),
                    items: _doctors
                        .map((d) => DropdownMenuItem(value: d['id'] as String, child: Text(d['name'] as String)))
                        .toList(),
                    onChanged: (v) async {
                      setState(() => _doctorId = v);
                      await _loadSlots();
                    },
                  ),
                  const SizedBox(height: 12),
                  if (_slots.isEmpty)
                    const Text('Aucun créneau disponible.', style: TextStyle(color: Colors.grey))
                  else
                    DropdownButtonFormField<String>(
                      value: _selectedSlot,
                      decoration: const InputDecoration(labelText: 'Créneau', border: OutlineInputBorder()),
                      items: _slots
                          .map((s) => DropdownMenuItem(
                                value: s['scheduled_at'] as String,
                                child: Text(_fmt(s['scheduled_at'] as String?)),
                              ))
                          .toList(),
                      onChanged: (v) => setState(() => _selectedSlot = v),
                    ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _reasonCtrl,
                    decoration: const InputDecoration(labelText: 'Motif', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: _selectedSlot != null ? _book : null,
                    icon: const Icon(Icons.check),
                    label: const Text('Confirmer le rendez-vous'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Mes rendez-vous (${_appointments.length})', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ..._appointments.map((a) => Card(
                elevation: 0,
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Colors.teal.shade100,
                    child: const Icon(Icons.event, color: Colors.teal),
                  ),
                  title: Text(a['doctor_name'] as String? ?? 'Médecin'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_fmt(a['scheduled_at'] as String?)),
                      if ((a['reason'] as String?)?.isNotEmpty == true)
                        Text(a['reason'] as String, style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                    ],
                  ),
                  trailing: Chip(label: Text(_statusLabel(a['status'] as String?))),
                ),
              )),
          if (_appointments.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: Text('Aucun rendez-vous pour le moment.', style: TextStyle(color: Colors.grey))),
            ),
        ],
      ),
    );
  }
}

class InvoicesTab extends StatefulWidget {
  final String patientPhone;
  const InvoicesTab({super.key, required this.patientPhone});

  @override
  State<InvoicesTab> createState() => _InvoicesTabState();
}

class _InvoicesTabState extends State<InvoicesTab> {
  List<dynamic> _invoices = [];
  bool _loading = true;
  String? _declaringId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final list = await ApiService.getMyInvoices();
    if (mounted) setState(() {
      _invoices = list;
      _loading = false;
    });
  }

  String _fmtMoney(String? v) {
    final n = double.tryParse(v ?? '') ?? 0;
    return '${NumberFormat('#,##0', 'fr_FR').format(n)} FCFA';
  }

  String _statusLabel(String? s) {
    switch (s) {
      case 'ISSUED':
        return 'Émise';
      case 'PARTIAL':
        return 'Partielle';
      case 'PAID':
        return 'Payée';
      default:
        return s ?? '';
    }
  }

  Future<void> _openDeclareSheet(Map<String, dynamic> invoice) async {
    final phoneCtrl = TextEditingController(text: widget.patientPhone);
    final refCtrl = TextEditingController();
    var method = 'AIRTEL';

    final result = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: StatefulBuilder(
            builder: (ctx, setLocal) => Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  invoice['invoice_number'] as String? ?? 'Facture',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                ),
                Text(
                  'Reste à payer : ${_fmtMoney(invoice['balance_due'] as String?)}',
                  style: TextStyle(color: Colors.grey.shade700),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: phoneCtrl,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'N° Mobile Money (Airtel / MTN)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: method,
                  decoration: const InputDecoration(labelText: 'Réseau', border: OutlineInputBorder()),
                  items: const [
                    DropdownMenuItem(value: 'AIRTEL', child: Text('Airtel Money')),
                    DropdownMenuItem(value: 'MTN', child: Text('MTN Mobile Money')),
                  ],
                  onChanged: (v) => setLocal(() => method = v ?? 'AIRTEL'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: refCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Réf. transaction (optionnel)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 20),
                FilledButton.icon(
                  onPressed: () => Navigator.pop(ctx, 'PAID'),
                  icon: const Icon(Icons.check_circle_outline),
                  label: const Text('J\'ai payé — valider'),
                  style: FilledButton.styleFrom(backgroundColor: Colors.teal),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => Navigator.pop(ctx, 'UNPAID'),
                  icon: const Icon(Icons.cancel_outlined),
                  label: const Text('Je n\'ai pas payé'),
                ),
              ],
            ),
          ),
        );
      },
    );

    if (result == null || !mounted) return;
    if (phoneCtrl.text.trim().length < 8) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Saisissez votre numéro Mobile Money')),
      );
      return;
    }

    setState(() => _declaringId = invoice['id'] as String);
    final res = await ApiService.declareInvoicePayment(
      invoiceId: invoice['id'] as String,
      phoneNumber: phoneCtrl.text.trim(),
      method: method,
      declaration: result,
      transactionReference: refCtrl.text.trim(),
    );
    if (!mounted) return;
    setState(() => _declaringId = null);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          res.ok
              ? (result == 'PAID' ? 'Paiement enregistré — facture mise à jour' : 'Déclaration impayée envoyée')
              : (res.error ?? 'Erreur'),
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Mes factures', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(
            'Validez le paiement depuis votre téléphone (Airtel / MTN).',
            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 16),
          if (_invoices.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 48),
              child: Center(child: Text('Aucune facture pour le moment', style: TextStyle(color: Colors.grey))),
            )
          else
            ..._invoices.map((inv) {
              final id = inv['id'] as String;
              final balance = double.tryParse(inv['balance_due'] as String? ?? '') ?? 0;
              final canPay = balance > 0 && inv['status'] != 'PAID';
              final decl = inv['patient_declaration'] as Map<String, dynamic>?;
              return Card(
                elevation: 0,
                margin: const EdgeInsets.only(bottom: 10),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              inv['invoice_number'] as String? ?? '',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                            ),
                          ),
                          Chip(
                            label: Text(_statusLabel(inv['status'] as String?), style: const TextStyle(fontSize: 11)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text('Part patient : ${_fmtMoney(inv['patient_amount'] as String?)}'),
                      Text(
                        'Reste dû : ${_fmtMoney(inv['balance_due'] as String?)}',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: balance > 0 ? Colors.red.shade700 : Colors.teal.shade700,
                        ),
                      ),
                      if (decl != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          decl['status'] == 'PAID'
                              ? '✓ Vous avez déclaré payé (${decl['phone_number']})'
                              : '✗ Vous avez déclaré impayé (${decl['phone_number']})',
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                        ),
                      ],
                      if (canPay) ...[
                        const SizedBox(height: 12),
                        FilledButton(
                          onPressed: _declaringId == id ? null : () => _openDeclareSheet(inv),
                          child: _declaringId == id
                              ? const SizedBox(
                                  height: 18,
                                  width: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : const Text('Valider paiement / impayé'),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}

class DossierTab extends StatefulWidget {
  final String patientId;
  final Map<String, dynamic> patient;

  const DossierTab({super.key, required this.patientId, required this.patient});

  @override
  State<DossierTab> createState() => _DossierTabState();
}

class _DossierTabState extends State<DossierTab> {
  int _section = 0;

  static const _sections = ['Documents', 'Soins', 'Médecin', 'Rappels'];

  String _genderLabel(String? g) {
    switch (g) {
      case 'M':
        return 'Masculin';
      case 'F':
        return 'Féminin';
      default:
        return g ?? '—';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Mon dossier médical', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(
                'Documents, carte patient PDF et suivi médical',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
              ),
              const SizedBox(height: 12),
              Card(
                elevation: 0,
                color: const Color(0xFFF1F5F9),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${widget.patient['last_name']} ${widget.patient['first_name']}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 4),
                      Text('N° dossier : ${widget.patient['id']}', style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
                      if ((widget.patient['email'] as String?)?.isNotEmpty == true)
                        Text(widget.patient['email'] as String, style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
                      Text(
                        'Sexe : ${_genderLabel(widget.patient['gender'] as String?)}',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: List.generate(_sections.length, (i) {
                    final selected = _section == i;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(_sections[i]),
                        selected: selected,
                        onSelected: (_) => setState(() => _section = i),
                        selectedColor: Colors.teal.shade100,
                        checkmarkColor: Colors.teal.shade800,
                      ),
                    );
                  }),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: IndexedStack(
            index: _section,
            children: [
              _DossierDocumentsSection(patientId: widget.patientId),
              CarePlanTab(patientId: widget.patientId),
              ChatTab(patientId: widget.patientId),
              RemindersTab(patientId: widget.patientId),
            ],
          ),
        ),
      ],
    );
  }
}

class _DossierDocumentsSection extends StatefulWidget {
  final String patientId;
  const _DossierDocumentsSection({required this.patientId});

  @override
  State<_DossierDocumentsSection> createState() => _DossierDocumentsSectionState();
}

class _DossierDocumentsSectionState extends State<_DossierDocumentsSection> {
  List<dynamic> _docs = [];
  List<dynamic> _doctors = [];
  String? _doctorId;
  bool _loading = true;
  bool _downloadingCard = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final docs = widget.patientId.isEmpty
        ? <dynamic>[]
        : await ApiService.getDocuments(patientId: widget.patientId);
    final doctors = await ApiService.getDoctors();
    if (mounted) {
      setState(() {
        _docs = docs;
        _doctors = doctors;
        _doctorId ??= doctors.isNotEmpty ? doctors.first['id'] as String : null;
        _loading = false;
      });
    }
  }

  Future<void> _downloadIdentityCard() async {
    setState(() => _downloadingCard = true);
    final bytes = await ApiService.downloadPatientIdentityPdf(doctorId: _doctorId);
    if (!mounted) return;
    setState(() => _downloadingCard = false);
    if (bytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Impossible de générer la carte patient')),
      );
      return;
    }
    final path = await savePdfBytes(bytes, 'carte-patient-sghl');
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(path != null ? 'Carte patient enregistrée : $path' : 'Carte patient téléchargée'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _download(Map<String, dynamic> d) async {
    final bytes = await ApiService.downloadDocument(d['id'] as String);
    if (!mounted || bytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Téléchargement impossible')));
      return;
    }
    final path = await savePdfBytes(bytes, d['title'] as String? ?? 'document');
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(path != null ? 'Document enregistré : $path' : 'Document téléchargé'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: Colors.teal.shade100),
            ),
            color: Colors.teal.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Icon(Icons.badge_outlined, color: Colors.teal.shade700),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Ma carte patient (PDF)',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Le QR ouvre une page avec vos diagnostics (CIM-10), notes du médecin '
                    'et ordonnances, en plus de vos identifiants.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade700, height: 1.35),
                  ),
                  const SizedBox(height: 12),
                  if (_doctors.isEmpty)
                    const Text('Aucun médecin disponible.', style: TextStyle(color: Colors.grey))
                  else
                    DropdownButtonFormField<String>(
                      value: _doctorId,
                      decoration: const InputDecoration(
                        labelText: 'Médecin référent',
                        border: OutlineInputBorder(),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                      items: _doctors
                          .map((d) => DropdownMenuItem(
                                value: d['id'] as String,
                                child: Text(d['name'] as String? ?? 'Médecin'),
                              ))
                          .toList(),
                      onChanged: (v) => setState(() => _doctorId = v),
                    ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _doctorId != null && !_downloadingCard ? _downloadIdentityCard : null,
                    icon: _downloadingCard
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.qr_code_2),
                    label: Text(_downloadingCard ? 'Génération…' : 'Télécharger ma carte PDF'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text('Autres documents', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Résultats, factures et comptes-rendus déposés par l\'hôpital',
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 8),
          if (_docs.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(child: Text('Aucun document disponible', style: TextStyle(color: Colors.grey))),
            )
          else
            ..._docs.map((d) => Card(
                  elevation: 0,
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(Icons.picture_as_pdf, color: Colors.red, size: 32),
                    title: Text(d['title'] as String? ?? 'Document'),
                    subtitle: Text(d['document_type'] as String? ?? ''),
                    trailing: const Icon(Icons.download_rounded),
                    onTap: () => _download(d),
                  ),
                )),
        ],
      ),
    );
  }
}

class CarePlanTab extends StatefulWidget {
  final String patientId;
  const CarePlanTab({super.key, required this.patientId});

  @override
  State<CarePlanTab> createState() => _CarePlanTabState();
}

class _CarePlanTabState extends State<CarePlanTab> {
  List<dynamic> _tasks = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (widget.patientId.isEmpty) return;
    final tasks = await ApiService.getCareTasks(widget.patientId);
    if (mounted) setState(() => _tasks = tasks);
  }

  Color _statusColor(String? s) {
    switch (s) {
      case 'DONE':
        return Colors.green;
      case 'MISSED':
        return Colors.red;
      default:
        return Colors.orange;
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: _tasks.isEmpty
          ? ListView(children: const [SizedBox(height: 120), Center(child: Text('Aucun soin planifié'))])
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _tasks.length,
              itemBuilder: (_, i) {
                final t = _tasks[i];
                return Card(
                  elevation: 0,
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: Icon(Icons.healing, color: _statusColor(t['status'] as String?)),
                    title: Text(t['description'] as String? ?? ''),
                    subtitle: Text('${t['plan_title']} · ${t['scheduled_at']}'),
                    trailing: Chip(
                      label: Text(t['status'] as String? ?? '', style: const TextStyle(fontSize: 11)),
                      backgroundColor: _statusColor(t['status'] as String?).withValues(alpha: 0.15),
                    ),
                  ),
                );
              },
            ),
    );
  }
}

class ChatTab extends StatefulWidget {
  final String patientId;
  const ChatTab({super.key, required this.patientId});

  @override
  State<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends State<ChatTab> {
  List<dynamic> _messages = [];
  final _ctrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (widget.patientId.isEmpty) return;
    final msgs = await ApiService.getChat(widget.patientId);
    if (mounted) setState(() => _messages = msgs);
  }

  Future<void> _send() async {
    if (_ctrl.text.trim().isEmpty) return;
    await ApiService.sendChat(widget.patientId, _ctrl.text.trim());
    _ctrl.clear();
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
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
                      hintText: 'Message au médecin…',
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

class RemindersTab extends StatefulWidget {
  final String patientId;
  const RemindersTab({super.key, required this.patientId});

  @override
  State<RemindersTab> createState() => _RemindersTabState();
}

class _RemindersTabState extends State<RemindersTab> {
  List<dynamic> _reminders = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (widget.patientId.isEmpty) return;
    final r = await ApiService.getReminders(widget.patientId);
    if (mounted) setState(() => _reminders = r);
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: _reminders.isEmpty
          ? ListView(children: const [SizedBox(height: 120), Center(child: Text('Aucun rappel médicament'))])
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _reminders.length,
              itemBuilder: (_, i) {
                final r = _reminders[i];
                return Card(
                  elevation: 0,
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(Icons.alarm, color: Colors.orange),
                    title: Text(r['medicine_name'] as String? ?? ''),
                    subtitle: Text('${r['dosage']} — ${r['schedule_time']}'),
                  ),
                );
              },
            ),
    );
  }
}

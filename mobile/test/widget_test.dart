import 'package:flutter_test/flutter_test.dart';
import 'package:sghl_mobile/main.dart';

void main() {
  testWidgets('SGHL app démarre sur l\'écran portail', (WidgetTester tester) async {
    await tester.pumpWidget(const SghlApp());
    await tester.pumpAndSettle(const Duration(seconds: 2));
    expect(find.text('SGHL Mobile'), findsOneWidget);
    expect(find.text('Espace patient'), findsOneWidget);
    expect(find.text('Espace médecin'), findsOneWidget);
  });
}

// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

Future<String?> savePdfBytes(List<int> bytes, String filename) async {
  final safeName = filename.replaceAll(RegExp(r'[^\w\-]'), '_');
  final blob = html.Blob([bytes], 'application/pdf');
  final url = html.Url.createObjectUrlFromBlob(blob);
  html.AnchorElement(href: url)
    ..setAttribute('download', '$safeName.pdf')
    ..click();
  html.Url.revokeObjectUrl(url);
  return '$safeName.pdf';
}

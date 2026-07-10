import 'dart:io';

import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

Future<String?> savePdfBytes(List<int> bytes, String filename) async {
  final dir = await getApplicationDocumentsDirectory();
  final safeName = filename.replaceAll(RegExp(r'[^\w\-]'), '_');
  final file = File('${dir.path}/$safeName.pdf');
  await file.writeAsBytes(bytes);
  await OpenFile.open(file.path);
  return file.path;
}

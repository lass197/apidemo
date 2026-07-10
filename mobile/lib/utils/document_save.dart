export 'document_save_stub.dart'
    if (dart.library.io) 'document_save_io.dart'
    if (dart.library.html) 'document_save_web.dart';

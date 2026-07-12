"""Vues utilitaires SGHL (serving frontend SPA)."""

import mimetypes

from django.conf import settings
from django.http import FileResponse, HttpResponse


def serve_frontend(request, resource=""):
    """Sert le build Vue.js — fallback index.html pour le history mode."""
    dist = settings.FRONTEND_DIST

    if resource:
        target = dist / resource
        if target.is_file():
            content_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(
                target.open("rb"),
                content_type=content_type or "application/octet-stream",
            )

    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")

    return HttpResponse(
        """
        <!DOCTYPE html>
        <html lang="fr"><head><meta charset="utf-8"><title>SGHL</title></head>
        <body style="font-family:sans-serif;max-width:600px;margin:3rem auto;padding:1rem">
          <h1>SGHL — Frontend non compilé</h1>
          <p>Le dossier <code>frontend/dist</code> est absent.</p>
          <h3>Option 1 — Développement (recommandé)</h3>
          <pre>cd frontend\nnpm install\nnpm run dev</pre>
          <p>Puis ouvrez <a href="http://localhost:5173">http://localhost:5173</a></p>
          <h3>Option 2 — Build production</h3>
          <pre>cd frontend\nnpm install\nnpm run build</pre>
          <p>Puis rechargez <a href="/">http://127.0.0.1:8000/</a></p>
          <hr>
          <p><a href="/admin/">Console admin SGHL</a> · <a href="/api/v1/docs">Documentation API</a></p>
        </body></html>
        """,
        content_type="text/html; charset=utf-8",
    )


def serve_admin(request, resource=""):
    """Sert la console admin Vue.js — fallback index.html pour le history mode."""
    dist = settings.ADMIN_DIST

    if resource:
        target = dist / resource
        if target.is_file():
            content_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(
                target.open("rb"),
                content_type=content_type or "application/octet-stream",
            )

    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")

    return HttpResponse(
        """
        <!DOCTYPE html>
        <html lang="fr"><head><meta charset="utf-8"><title>SGHL Admin</title></head>
        <body style="font-family:sans-serif;max-width:600px;margin:3rem auto;padding:1rem">
          <h1>SGHL — Console admin non compilée</h1>
          <p>Le dossier <code>admin/dist</code> est absent.</p>
          <h3>Option 1 — Développement</h3>
          <pre>cd admin\nnpm install\nnpm run dev</pre>
          <p>Puis ouvrez <a href="http://localhost:5174">http://localhost:5174</a></p>
          <h3>Option 2 — Build production</h3>
          <pre>cd admin\nnpm install\nnpm run build</pre>
          <p>Puis rechargez <a href="/admin/">http://127.0.0.1:8000/admin/</a></p>
        </body></html>
        """,
        content_type="text/html; charset=utf-8",
    )


def serve_mobile(request, resource=""):
    """Sert le build Flutter Web sous /m/ — fallback index.html."""
    dist = settings.MOBILE_DIST

    if resource:
        target = dist / resource
        if target.is_file():
            content_type, _ = mimetypes.guess_type(str(target))
            return FileResponse(
                target.open("rb"),
                content_type=content_type or "application/octet-stream",
            )

    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")

    return HttpResponse(
        """
        <!DOCTYPE html>
        <html lang="fr"><head><meta charset="utf-8"><title>SGHL Mobile</title></head>
        <body style="font-family:sans-serif;max-width:600px;margin:3rem auto;padding:1rem">
          <h1>SGHL — App mobile non compilée</h1>
          <p>Le dossier <code>mobile/dist</code> est absent.</p>
          <pre>cd mobile
flutter build web --release --base-href /m/ --dart-define=API_BASE=/api/v1
# puis copier build/web vers mobile/dist</pre>
          <p><a href="/">Staff</a> · <a href="/admin/">Admin</a> · <a href="/api/v1/docs">API</a></p>
        </body></html>
        """,
        content_type="text/html; charset=utf-8",
    )

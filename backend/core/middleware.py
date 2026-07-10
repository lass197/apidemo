import ipaddress
import threading

_thread_locals = threading.local()


def get_current_request():
    return getattr(_thread_locals, "request", None)


def get_client_ip(request) -> str | None:
    """IP client compatible Render (X-Forwarded-For) et GenericIPAddressField."""
    candidates: list[str] = []
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        candidates.extend(part.strip() for part in x_forwarded.split(",") if part.strip())
    remote = request.META.get("REMOTE_ADDR")
    if remote:
        candidates.append(remote.strip())

    for raw in candidates:
        # Enlever un éventuel port (ex. 1.2.3.4:12345)
        host = raw
        if host.startswith("["):
            # IPv6 entre crochets [::1]:port
            end = host.find("]")
            if end != -1:
                host = host[1:end]
        elif host.count(":") == 1 and "." in host:
            host = host.split(":", 1)[0]
        try:
            return str(ipaddress.ip_address(host))
        except ValueError:
            continue
    return None


class AuditContextMiddleware:
    """Expose la requête courante pour l'audit trail."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            _thread_locals.request = None

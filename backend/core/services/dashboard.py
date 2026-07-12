from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from billing.models import Invoice
from clinical.models import Bed, Hospitalization
from laboratory.models import LabOrder


CACHE_TTL = 60
CACHE_KEY = "sghl_dashboard_kpis"


def _cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        return None


def _cache_set(key, value, ttl):
    try:
        cache.set(key, value, ttl)
    except Exception:
        pass


def get_dashboard_kpis() -> dict:
    cached = _cache_get(CACHE_KEY)
    if cached:
        return cached

    total_beds = Bed.objects.filter(is_active=True).count()
    occupied = Bed.objects.filter(status=Bed.OCCUPIED, is_active=True).count()
    occupancy_rate = round((occupied / total_beds * 100) if total_beds else 0, 1)

    today = timezone.now().date()
    revenue_today = (
        Invoice.objects.filter(
            issued_at__date=today,
            status__in=[Invoice.ISSUED, Invoice.PARTIAL, Invoice.PAID],
        ).aggregate(total=Sum("paid_amount"))["total"]
        or Decimal("0")
    )

    pending_labs = LabOrder.objects.filter(
        status__in=[LabOrder.ORDERED, LabOrder.COLLECTED, LabOrder.ASSIGNED, LabOrder.RESULTS_ENTERED]
    ).count()

    active_hospitalizations = Hospitalization.objects.filter(status=Hospitalization.ACTIVE).count()

    kpis = {
        "occupancy_rate": occupancy_rate,
        "occupied_beds": occupied,
        "total_beds": total_beds,
        "revenue_today": str(revenue_today),
        "pending_lab_exams": pending_labs,
        "active_hospitalizations": active_hospitalizations,
        "generated_at": timezone.now().isoformat(),
    }
    _cache_set(CACHE_KEY, kpis, CACHE_TTL)
    return kpis


def invalidate_dashboard_cache():
    try:
        cache.delete(CACHE_KEY)
    except Exception:
        pass

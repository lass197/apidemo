from django.db.models import Q


def filter_by_patient_name(qs, search: str, *, prefix: str = ""):
    """Filtre par nom/prénom — chaque mot doit correspondre (ex. « Lass Bayendat »)."""
    term = (search or "").strip()
    if not term:
        return qs
    first = f"{prefix}first_name__icontains"
    last = f"{prefix}last_name__icontains"
    words = [w for w in term.split() if len(w) >= 2]
    if not words:
        words = [term]
    for word in words:
        qs = qs.filter(Q(**{first: word}) | Q(**{last: word}))
    return qs

"""Informations publiques sur l'établissement SGHL — Dolisie, République du Congo."""

from urllib.parse import quote_plus

# Coordonnées approximatives — Quartier Gaïa, Dolisie
HOSPITAL_LAT = -4.1990
HOSPITAL_LNG = 12.6730
HOSPITAL_MAP_ZOOM = 16

_MAP_QUERY = quote_plus(
    "35 Rue Mali, Quartier Gaïa, Dolisie, République du Congo"
)
_GOOGLE_EMBED = (
    f"https://maps.google.com/maps?q={_MAP_QUERY}"
    f"&hl=fr&z={HOSPITAL_MAP_ZOOM}&output=embed"
)
_GOOGLE_EMBED_COORDS = (
    f"https://maps.google.com/maps?q={HOSPITAL_LAT},{HOSPITAL_LNG}"
    f"&hl=fr&z={HOSPITAL_MAP_ZOOM}&output=embed"
)

HOSPITAL_PROFILE = {
    "name": "Centre Hospitalier SGHL",
    "tagline": "La Terre Jaune — soins de proximité à Dolisie",
    "country": "République du Congo",
    "country_code": "RC",
    "country_display": "République du Congo (RC)",
    "city": "Dolisie",
    "city_nickname": "La Terre Jaune",
    "neighborhood": "Quartier Gaïa",
    "street": "Rue Mali",
    "street_number": "35",
    "landmark": "En face du consistoire de l'Église Évangélique du Congo (EEC)",
    "address": (
        "35, Rue Mali — Quartier Gaïa, Dolisie (La Terre Jaune), "
        "République du Congo (RC)"
    ),
    "address_lines": [
        "35, Rue Mali",
        "Quartier Gaïa — en face du consistoire EEC",
        "Dolisie · La Terre Jaune",
        "République du Congo (RC)",
    ],
    "phone": "06 904 89 62",
    "phone_tel": "+242069048962",
    "emergency_phones": [
        {"label": "Urgences — ligne 1", "display": "06 904 89 62", "tel": "+242069048962"},
        {"label": "Urgences — ligne 2", "display": "06 659 25 64", "tel": "+242066592564"},
        {"label": "Urgences — ligne 3", "display": "06 828 82 37", "tel": "+242068288237"},
    ],
    "emergency_phone": "06 904 89 62 · 06 659 25 64 · 06 828 82 37",
    "email": "accueil@sghl.cg",
    "website": "https://sghl.cg",
    "opening_hours": "Accueil : lun–ven 7h–20h, sam 8h–14h",
    "emergency_hours": "Urgences : 24h/24, 7j/7 — 3 lignes dédiées",
    "location": {
        "latitude": HOSPITAL_LAT,
        "longitude": HOSPITAL_LNG,
        "zoom": HOSPITAL_MAP_ZOOM,
    },
    "map": {
        "provider": "google",
        "google_embed_url": _GOOGLE_EMBED,
        "google_embed_url_coords": _GOOGLE_EMBED_COORDS,
        "embed_url": _GOOGLE_EMBED,
        "openstreetmap_embed_url": (
            "https://www.openstreetmap.org/export/embed.html"
            f"?bbox={HOSPITAL_LNG - 0.008}%2C{HOSPITAL_LAT - 0.008}"
            f"%2C{HOSPITAL_LNG + 0.008}%2C{HOSPITAL_LAT + 0.008}"
            f"&layer=mapnik&marker={HOSPITAL_LAT}%2C{HOSPITAL_LNG}"
        ),
        "openstreetmap_url": f"https://www.openstreetmap.org/?mlat={HOSPITAL_LAT}&mlon={HOSPITAL_LNG}#map={HOSPITAL_MAP_ZOOM}/{HOSPITAL_LAT}/{HOSPITAL_LNG}",
        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={HOSPITAL_LAT},{HOSPITAL_LNG}",
        "google_maps_directions_url": f"https://www.google.com/maps/dir/?api=1&destination={HOSPITAL_LAT},{HOSPITAL_LNG}&travelmode=driving",
        "directions_hint": "Quartier Gaïa — repère : consistoire de l'Église Évangélique du Congo (EEC), Rue Mali",
        "static_image_url": (
            "https://staticmap.openstreetmap.de/staticmap.php"
            f"?center={HOSPITAL_LAT},{HOSPITAL_LNG}&zoom={HOSPITAL_MAP_ZOOM}"
            f"&size=900x480&maptype=mapnik"
            f"&markers={HOSPITAL_LAT},{HOSPITAL_LNG},red-pushpin"
        ),
    },
    "about": (
        "Le Centre Hospitalier SGHL est un établissement de santé de référence à Dolisie, "
        "capitale économique du Niari, surnommée « La Terre Jaune ». Implanté au cœur du "
        "quartier Gaïa, nous accueillons patients et familles dans un cadre moderne, "
        "accessible et ancré dans la communauté locale."
    ),
    "mission": (
        "Offrir des soins de qualité, accessibles et humains à la population de Dolisie "
        "et des environs, en coordonnant urgences, hospitalisation, consultations "
        "spécialisées, laboratoire et pharmacie au sein d'un parcours de soins fluide."
    ),
    "stats": [
        {"value": "120", "label": "Lits"},
        {"value": "24/7", "label": "Urgences"},
        {"value": "16+", "label": "Médecins"},
        {"value": "9", "label": "Services"},
    ],
    "highlights": [
        {"icon": "🚑", "title": "Urgences 24/7", "text": "Trois lignes d'urgence actives — prise en charge immédiate"},
        {"icon": "📍", "title": "Quartier Gaïa", "text": "Rue Mali n° 35, face au consistoire EEC — accès facile"},
        {"icon": "❤️", "title": "Cardiologie", "text": "Unité de soins cardiovasculaires et suivi post-opératoire"},
        {"icon": "👶", "title": "Pédiatrie", "text": "Consultations enfants & adolescents — étage 3, salles 301-302"},
        {"icon": "🔬", "title": "Laboratoire", "text": "Analyses biologiques — résultats disponibles en ligne"},
        {"icon": "💊", "title": "Pharmacie", "text": "Pharmacie hospitalière et dispensation sécurisée"},
        {"icon": "📱", "title": "Portail patient", "text": "Rendez-vous en ligne, documents médicaux et suivi de séjour"},
    ],
    "departments": [
        {"code": "URG", "name": "Urgences", "floor": "Rez-de-chaussée", "phone": "06 904 89 62", "hours": "24h/24"},
        {"code": "CARDIO", "name": "Cardiologie", "floor": "Étage 2", "phone": "06 659 25 64", "hours": "8h–18h"},
        {"code": "LAB", "name": "Laboratoire", "floor": "Étage 1", "phone": "06 828 82 37", "hours": "7h–19h"},
        {"code": "RAD", "name": "Imagerie", "floor": "Étage 1", "phone": "06 659 25 64", "hours": "8h–17h"},
        {"code": "PEDIA", "name": "Pédiatrie", "floor": "Étage 3", "phone": "06 659 25 64", "hours": "8h–20h"},
        {"code": "MAT", "name": "Maternité", "floor": "Étage 3", "phone": "06 904 89 62", "hours": "24h/24"},
    ],
    "amenities": [
        {"icon": "⛪", "title": "Repère EEC", "text": "En face du consistoire — Église Évangélique du Congo"},
        {"icon": "🅿️", "title": "Parking", "text": "Stationnement visiteurs Rue Mali"},
        {"icon": "☕", "title": "Espace famille", "text": "Salon d'attente et accueil visiteurs"},
        {"icon": "♿", "title": "Accessibilité", "text": "Accès de plain-pied au rez-de-chaussée"},
    ],
    "faq": [
        {
            "q": "Comment nous trouver ?",
            "a": (
                "Nous sommes au 35, Rue Mali, quartier Gaïa à Dolisie, "
                "en face du consistoire de l'Église Évangélique du Congo (EEC). "
                "Utilisez la carte interactive sur cette page pour vous orienter."
            ),
        },
        {
            "q": "Comment prendre rendez-vous ?",
            "a": (
                "Via le portail patient en ligne, par téléphone au 06 904 89 62, "
                "ou sur place à l'accueil (lun–ven 7h–20h, sam 8h–14h)."
            ),
        },
        {
            "q": "Quels numéros appeler en urgence ?",
            "a": (
                "Composez l'un des trois numéros d'urgence : 06 904 89 62, "
                "06 659 25 64 ou 06 828 82 37 — disponibles 24h/24."
            ),
        },
        {
            "q": "Dois-je apporter des documents ?",
            "a": (
                "Pièce d'identité, carte CMU ou attestation mutuelle, ordonnances en cours "
                "et résultats d'examens récents le cas échéant."
            ),
        },
        {
            "q": "Comment accéder à mes résultats ?",
            "a": "Connectez-vous à votre espace patient — onglet « Mon dossier ».",
        },
    ],
}

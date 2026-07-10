/** Coordonnées & liens carte — Centre Hospitalier SGHL, Dolisie (fallback si API indisponible). */

export const HOSPITAL_LAT = -4.199
export const HOSPITAL_LNG = 12.673
export const HOSPITAL_ZOOM = 16

const QUERY = encodeURIComponent(
  '35 Rue Mali, Quartier Gaïa, Dolisie, République du Congo RC',
)

export const HOSPITAL_MAP_LINKS = {
  googleEmbedUrl: `https://maps.google.com/maps?q=${QUERY}&hl=fr&z=${HOSPITAL_ZOOM}&output=embed`,
  googleEmbedCoords: `https://maps.google.com/maps?q=${HOSPITAL_LAT},${HOSPITAL_LNG}&hl=fr&z=${HOSPITAL_ZOOM}&output=embed`,
  googleMapsUrl: `https://www.google.com/maps/search/?api=1&query=${HOSPITAL_LAT},${HOSPITAL_LNG}`,
  googleDirectionsUrl: `https://www.google.com/maps/dir/?api=1&destination=${HOSPITAL_LAT},${HOSPITAL_LNG}&travelmode=driving`,
  openStreetMapEmbed: `https://www.openstreetmap.org/export/embed.html?bbox=${HOSPITAL_LNG - 0.012}%2C${HOSPITAL_LAT - 0.012}%2C${HOSPITAL_LNG + 0.012}%2C${HOSPITAL_LAT + 0.012}&layer=mapnik&marker=${HOSPITAL_LAT}%2C${HOSPITAL_LNG}`,
}

export function resolveHospitalMap(hospital) {
  const m = hospital?.map || {}
  const loc = hospital?.location || {}
  const lat = loc.latitude ?? HOSPITAL_LAT
  const lng = loc.longitude ?? HOSPITAL_LNG

  return {
    googleEmbedUrl:
      m.google_embed_url || m.embed_url || HOSPITAL_MAP_LINKS.googleEmbedUrl,
    googleMapsUrl:
      m.google_maps_url ||
      `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`,
    googleDirectionsUrl:
      m.google_maps_directions_url ||
      `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`,
    openStreetMapEmbed:
      m.openstreetmap_embed_url || HOSPITAL_MAP_LINKS.openStreetMapEmbed,
  }
}

export const HOSPITAL_ADDRESS = {
  name: 'Centre Hospitalier SGHL',
  city: 'Dolisie',
  cityNickname: 'La Terre Jaune',
  country: 'République du Congo',
  countryCode: 'RC',
  countryDisplay: 'République du Congo (RC)',
  neighborhood: 'Quartier Gaïa',
  street: 'Rue Mali',
  streetNumber: '35',
  landmark: "En face du consistoire de l'Église Évangélique du Congo (EEC)",
  full: '35, Rue Mali — Quartier Gaïa, Dolisie (La Terre Jaune), République du Congo (RC)',
}

export function formatCountryDisplay(hospital) {
  if (hospital?.country_display) return hospital.country_display
  const code = hospital?.country_code || HOSPITAL_ADDRESS.countryCode
  const name = hospital?.country || HOSPITAL_ADDRESS.country
  return `${name} (${code})`
}

/** Corrige d'anciens libellés « RDC » (rez-de-chaussée) dans les fiches services. */
export function normalizeServiceLocationHint(hint) {
  return (hint || '')
    .replace(/\bRDC\b/g, 'Rez-de-chaussée')
    .replace(/\bRépublique Démocratique du Congo\b/gi, 'République du Congo')
}

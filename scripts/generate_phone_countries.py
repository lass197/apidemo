"""Génère frontend/src/data/phoneCountries.json — tous les pays + Congo-Brazzaville."""
import json
from pathlib import Path

RAW = """
AF Afghanistan 93 9 9
AL Albania 355 8 9
DZ Algeria 213 9 9
AD Andorra 376 6 9
AO Angola 244 9 9
AG Antigua and Barbuda 1 10 10
AR Argentina 54 10 10
AM Armenia 374 8 8
AU Australia 61 9 9
AT Austria 43 10 13
AZ Azerbaijan 994 9 9
BS Bahamas 1 10 10
BH Bahrain 973 8 8
BD Bangladesh 880 10 10
BB Barbados 1 10 10
BY Belarus 375 9 9
BE Belgium 32 9 9
BZ Belize 501 7 7
BJ Benin 229 8 10
BT Bhutan 975 8 8
BO Bolivia 591 8 8
BA Bosnia and Herzegovina 387 8 8
BW Botswana 267 8 8
BR Brazil 55 10 11
BN Brunei 673 7 7
BG Bulgaria 359 9 9
BF Burkina Faso 226 8 8
BI Burundi 257 8 8
CV Cabo Verde 238 7 7
KH Cambodia 855 8 9
CM Cameroon 237 9 9
CA Canada 1 10 10
CF Central African Republic 236 8 8
TD Chad 235 8 8
CL Chile 56 9 9
CN China 86 11 11
CO Colombia 57 10 10
KM Comoros 269 7 7
CG Congo-Brazzaville 242 9 9
CD Congo-Kinshasa 243 9 9
CR Costa Rica 506 8 8
CI Cote d Ivoire 225 10 10
HR Croatia 385 8 9
CU Cuba 53 8 8
CY Cyprus 357 8 8
CZ Czechia 420 9 9
DK Denmark 45 8 8
DJ Djibouti 253 8 8
DM Dominica 1 10 10
DO Dominican Republic 1 10 10
EC Ecuador 593 9 9
EG Egypt 20 10 10
SV El Salvador 503 8 8
GQ Equatorial Guinea 240 9 9
ER Eritrea 291 7 7
EE Estonia 372 7 8
SZ Eswatini 268 8 8
ET Ethiopia 251 9 9
FJ Fiji 679 7 7
FI Finland 358 9 10
FR France 33 9 9
GA Gabon 241 8 8
GM Gambia 220 7 7
GE Georgia 995 9 9
DE Germany 49 10 11
GH Ghana 233 9 9
GR Greece 30 10 10
GD Grenada 1 10 10
GT Guatemala 502 8 8
GN Guinea 224 9 9
GW Guinea-Bissau 245 7 7
GY Guyana 592 7 7
HT Haiti 509 8 8
HN Honduras 504 8 8
HK Hong Kong 852 8 8
HU Hungary 36 9 9
IS Iceland 354 7 9
IN India 91 10 10
ID Indonesia 62 9 11
IR Iran 98 10 10
IQ Iraq 964 10 10
IE Ireland 353 9 9
IL Israel 972 9 9
IT Italy 39 9 10
JM Jamaica 1 10 10
JP Japan 81 10 10
JO Jordan 962 9 9
KZ Kazakhstan 7 10 10
KE Kenya 254 9 9
KI Kiribati 686 5 8
KW Kuwait 965 8 8
KG Kyrgyzstan 996 9 9
LA Laos 856 9 10
LV Latvia 371 8 8
LB Lebanon 961 7 8
LS Lesotho 266 8 8
LR Liberia 231 8 9
LY Libya 218 9 9
LI Liechtenstein 423 7 9
LT Lithuania 370 8 8
LU Luxembourg 352 9 9
MO Macao 853 8 8
MG Madagascar 261 9 9
MW Malawi 265 9 9
MY Malaysia 60 9 10
MV Maldives 960 7 7
ML Mali 223 8 8
MT Malta 356 8 8
MH Marshall Islands 692 7 7
MR Mauritania 222 8 8
MU Mauritius 230 8 8
MX Mexico 52 10 10
FM Micronesia 691 7 7
MD Moldova 373 8 8
MC Monaco 377 8 9
MN Mongolia 976 8 8
ME Montenegro 382 8 8
MA Morocco 212 9 9
MZ Mozambique 258 9 9
MM Myanmar 95 8 10
NA Namibia 264 9 9
NR Nauru 674 7 7
NP Nepal 977 10 10
NL Netherlands 31 9 9
NZ New Zealand 64 8 10
NI Nicaragua 505 8 8
NE Niger 227 8 8
NG Nigeria 234 10 10
KP North Korea 850 8 10
MK North Macedonia 389 8 8
NO Norway 47 8 8
OM Oman 968 8 8
PK Pakistan 92 10 10
PW Palau 680 7 7
PS Palestine 970 9 9
PA Panama 507 8 8
PG Papua New Guinea 675 8 8
PY Paraguay 595 9 9
PE Peru 51 9 9
PH Philippines 63 10 10
PL Poland 48 9 9
PT Portugal 351 9 9
QA Qatar 974 8 8
RO Romania 40 9 9
RU Russia 7 10 10
RW Rwanda 250 9 9
KN Saint Kitts and Nevis 1 10 10
LC Saint Lucia 1 10 10
VC Saint Vincent and the Grenadines 1 10 10
WS Samoa 685 5 7
SM San Marino 378 8 10
ST Sao Tome and Principe 239 7 7
SA Saudi Arabia 966 9 9
SN Senegal 221 9 9
RS Serbia 381 8 9
SC Seychelles 248 7 7
SL Sierra Leone 232 8 8
SG Singapore 65 8 8
SK Slovakia 421 9 9
SI Slovenia 386 8 8
SB Solomon Islands 677 5 7
SO Somalia 252 8 9
ZA South Africa 27 9 9
KR South Korea 82 9 10
SS South Sudan 211 9 9
ES Spain 34 9 9
LK Sri Lanka 94 9 9
SD Sudan 249 9 9
SR Suriname 597 7 7
SE Sweden 46 9 9
CH Switzerland 41 9 9
SY Syria 963 9 9
TW Taiwan 886 9 9
TJ Tajikistan 992 9 9
TZ Tanzania 255 9 9
TH Thailand 66 9 9
TL Timor-Leste 670 8 8
TG Togo 228 8 8
TO Tonga 676 5 7
TT Trinidad and Tobago 1 10 10
TN Tunisia 216 8 8
TR Turkey 90 10 10
TM Turkmenistan 993 8 8
TV Tuvalu 688 5 6
UG Uganda 256 9 9
UA Ukraine 380 9 9
AE United Arab Emirates 971 9 9
GB United Kingdom 44 10 10
US United States 1 10 10
UY Uruguay 598 8 8
UZ Uzbekistan 998 9 9
VU Vanuatu 678 5 7
VA Vatican City 39 9 10
VE Venezuela 58 10 10
VN Vietnam 84 9 10
YE Yemen 967 9 9
ZM Zambia 260 9 9
ZW Zimbabwe 263 9 9
"""

FR_NAMES = {
    "CG": "Congo-Brazzaville",
    "CD": "Congo-Kinshasa (RDC)",
    "CI": "Côte d'Ivoire",
    "FR": "France",
    "SN": "Sénégal",
    "CM": "Cameroun",
    "GA": "Gabon",
    "US": "États-Unis",
    "GB": "Royaume-Uni",
    "DE": "Allemagne",
    "BE": "Belgique",
    "CH": "Suisse",
    "CA": "Canada",
}


def flag(iso: str) -> str:
    if len(iso) != 2:
        return ""
    return chr(0x1F1E6 + ord(iso[0]) - ord("A")) + chr(0x1F1E6 + ord(iso[1]) - ord("A"))


def main():
    out = []
    for line in RAW.strip().split("\n"):
        parts = line.split()
        iso = parts[0]
        dial = parts[-3]
        mx = int(parts[-1])
        mn = int(parts[-2])
        name = " ".join(parts[1:-3])
        if iso in FR_NAMES:
            name = FR_NAMES[iso]
        out.append({
            "code": iso,
            "name": name,
            "dial": dial,
            "flag": flag(iso),
            "min": mn,
            "max": mx,
            "example": "",
        })

    priority = ["SN", "CG", "CD", "FR", "CI", "CM", "GA"]
    top = [c for code in priority for c in out if c["code"] == code]
    rest = sorted([c for c in out if c["code"] not in priority], key=lambda x: x["name"])
    final = top + rest

    dest = Path(__file__).resolve().parents[1] / "frontend" / "src" / "data" / "phoneCountries.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
    print(f"{len(final)} pays -> {dest}")


if __name__ == "__main__":
    main()

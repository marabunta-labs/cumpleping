"""Time zones offered to the user and the phone prefix of each country."""
import pytz

DEFAULT_TIMEZONE = "Europe/Madrid"

# (label, IANA zone, phone prefix)
ZONES = [
    ("🇪🇸 España (Península)", "Europe/Madrid", "34"),
    ("🇪🇸 Canarias", "Atlantic/Canary", "34"),
    ("🇲🇽 México (Centro)", "America/Mexico_City", "52"),
    ("🇲🇽 México (Cancún)", "America/Cancun", "52"),
    ("🇲🇽 México (Sonora)", "America/Hermosillo", "52"),
    ("🇲🇽 México (Baja Cal.)", "America/Tijuana", "52"),
    ("🇨🇴 Colombia", "America/Bogota", "57"),
    ("🇵🇪 Perú", "America/Lima", "51"),
    ("🇦🇷 Argentina", "America/Argentina/Buenos_Aires", "54"),
    ("🇨🇱 Chile", "America/Santiago", "56"),
    ("🇻🇪 Venezuela", "America/Caracas", "58"),
    ("🇪🇨 Ecuador", "America/Guayaquil", "593"),
    ("🇺🇾 Uruguay", "America/Montevideo", "598"),
    ("🇧🇴 Bolivia", "America/La_Paz", "591"),
    ("🇵🇾 Paraguay", "America/Asuncion", "595"),
    ("🇨🇷 Costa Rica", "America/Costa_Rica", "506"),
    ("🇵🇦 Panamá", "America/Panama", "507"),
    ("🇩🇴 Rep. Dominicana", "America/Santo_Domingo", "1"),
    ("🇺🇸 EE.UU. (Este)", "America/New_York", "1"),
    ("🇺🇸 EE.UU. (Pacífico)", "America/Los_Angeles", "1"),
    ("🇵🇹 Portugal", "Europe/Lisbon", "351"),
    ("🇬🇧 Reino Unido", "Europe/London", "44"),
]

ENGLISH_LABELS = {
    "Europe/Madrid": "🇪🇸 Spain (Mainland)", "Atlantic/Canary": "🇪🇸 Canary Islands",
    "America/Mexico_City": "🇲🇽 Mexico (Central)", "America/Cancun": "🇲🇽 Mexico (Cancún)",
    "America/Hermosillo": "🇲🇽 Mexico (Sonora)", "America/Tijuana": "🇲🇽 Mexico (Baja Cal.)",
    "America/Bogota": "🇨🇴 Colombia", "America/Lima": "🇵🇪 Peru", "America/Argentina/Buenos_Aires": "🇦🇷 Argentina",
    "America/Santiago": "🇨🇱 Chile", "America/Caracas": "🇻🇪 Venezuela", "America/Guayaquil": "🇪🇨 Ecuador",
    "America/Montevideo": "🇺🇾 Uruguay", "America/La_Paz": "🇧🇴 Bolivia", "America/Asuncion": "🇵🇾 Paraguay",
    "America/Costa_Rica": "🇨🇷 Costa Rica", "America/Panama": "🇵🇦 Panama",
    "America/Santo_Domingo": "🇩🇴 Dominican Rep.", "America/New_York": "🇺🇸 USA (Eastern)",
    "America/Los_Angeles": "🇺🇸 USA (Pacific)", "Europe/Lisbon": "🇵🇹 Portugal", "Europe/London": "🇬🇧 United Kingdom",
}
_BY_ZONE = {tz: (label, prefix) for label, tz, prefix in ZONES}


def is_valid_timezone(name):
    return name in pytz.all_timezones_set


def timezone_label(tz, language="es"):
    if tz not in _BY_ZONE:
        return tz
    return ENGLISH_LABELS[tz] if language == "en" else _BY_ZONE[tz][0]


def zone_options(language="es"):
    """[(label, tz)] in the given language."""
    return [(timezone_label(tz, language), tz) for _, tz, _ in ZONES]


def phone_prefix(tz):
    """International prefix (without '+') of the zone's country; Spain if unknown."""
    return _BY_ZONE[tz][1] if tz in _BY_ZONE else "34"

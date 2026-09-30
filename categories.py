"""Contact categories. The key is what gets stored; labels are what the user sees."""
from i18n import DEFAULT_LANGUAGE

CATEGORY_KEYS = ["family", "friends", "partner", "work", "school", "sports", "neighbors", "none"]
DEFAULT_CATEGORY = "none"

LABELS = {
    "es": {"family": "👨‍👩‍👧 Familia", "friends": "🍻 Amigos", "partner": "💕 Pareja", "work": "💼 Trabajo",
           "school": "🎓 Estudios", "sports": "⚽ Deporte", "neighbors": "🏠 Vecinos", "none": "🤷 Ninguna"},
    "en": {"family": "👨‍👩‍👧 Family", "friends": "🍻 Friends", "partner": "💕 Partner", "work": "💼 Work",
           "school": "🎓 School", "sports": "⚽ Sports", "neighbors": "🏠 Neighbors", "none": "🤷 None"},
}

# Values stored by earlier versions (Spanish), used by the database migration
LEGACY_CATEGORIES = {
    "Familia": "family", "Amigos": "friends", "Trabajo": "work", "Ninguna": "none",
}


def categories(language=DEFAULT_LANGUAGE):
    """[(key, label)] in the given language."""
    labels = LABELS.get(language, LABELS[DEFAULT_LANGUAGE])
    return [(key, labels[key]) for key in CATEGORY_KEYS]


def category_label(key, language=DEFAULT_LANGUAGE):
    labels = LABELS.get(language, LABELS[DEFAULT_LANGUAGE])
    return labels.get(key, labels[DEFAULT_CATEGORY])

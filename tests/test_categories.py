from categories import CATEGORY_KEYS, DEFAULT_CATEGORY, LEGACY_CATEGORIES, categories, category_label
from messages import SUGGESTIONS, needs_age


def test_there_are_many_categories_and_a_default():
    assert len(categories()) >= 8
    assert DEFAULT_CATEGORY in CATEGORY_KEYS
    assert len(set(CATEGORY_KEYS)) == len(CATEGORY_KEYS)


def test_callback_data_has_no_underscores_in_keys():
    assert all("_" not in key for key in CATEGORY_KEYS)


def test_every_category_has_enough_suggestions_with_and_without_age():
    for key in CATEGORY_KEYS:
        for language in ("es", "en"):
            templates = SUGGESTIONS[language][key]
            assert len(templates) >= 5, (language, key)
            assert any(needs_age(t) for t in templates), (language, key)
            assert sum(not needs_age(t) for t in templates) >= 3, (language, key)


def test_legacy_categories_map_to_existing_keys():
    assert set(LEGACY_CATEGORIES.values()) <= set(CATEGORY_KEYS)


def test_unknown_category_label_falls_back():
    assert category_label("nope") == category_label(DEFAULT_CATEGORY)
    assert "Familia" in category_label("family")
    assert "Family" in category_label("family", "en")


def test_every_category_has_a_label_in_every_language():
    for language in ("es", "en"):
        assert [key for key, _ in categories(language)] == CATEGORY_KEYS

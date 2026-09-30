from zones import ZONES, is_valid_timezone, phone_prefix, timezone_label, zone_options


def test_all_offered_zones_are_valid():
    for _, tz, _ in ZONES:
        assert is_valid_timezone(tz), tz


def test_zone_callback_data_fits_telegram_limit():
    assert all(len(f"tz_{tz}".encode()) <= 64 for _, tz, _ in ZONES)


def test_is_valid_timezone():
    assert is_valid_timezone("America/Mexico_City")
    assert not is_valid_timezone("Marte/Olympus")


def test_phone_prefixes():
    assert phone_prefix("America/Mexico_City") == "52"
    assert phone_prefix("Europe/Madrid") == "34"
    assert phone_prefix("Asia/Tokyo") == "34"  # unknown: Spain by default


def test_label():
    assert "México" in timezone_label("America/Mexico_City")
    assert timezone_label("Asia/Tokyo") == "Asia/Tokyo"


def test_english_labels_exist_for_every_zone():
    for _, tz, _ in ZONES:
        assert timezone_label(tz, "en")
    assert timezone_label("America/Mexico_City", "en") == "🇲🇽 Mexico (Central)"
    assert [tz for _, tz in zone_options("en")] == [tz for _, tz, _ in ZONES]

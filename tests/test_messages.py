import random
import re
from datetime import date

import pytest

import messages
from age_facts import (FACTS, MAX_FACT_LENGTH, MAX_JOKE_LENGTH, facts_for_age, historical_entries, historical_facts)
from categories import CATEGORY_KEYS
from messages import CLOSERS, INTROS, SUGGESTIONS, needs_age, ordinal, pick_suggestion, render

BORN, TODAY = date(1996, 3, 5), date(2026, 3, 5)
LANGUAGES = ("es", "en")


def pick(category="friends", name="Ana", age=30, previous="", language="es"):
    return pick_suggestion(category, name, age, previous, language, BORN if age else None, TODAY)


def force_kind(monkeypatch, kind):
    monkeypatch.setattr(messages, "KIND_WEIGHTS", {k: (1 if k == kind else 0) for k in messages.KIND_WEIGHTS})


def greetings(language="es", age=30, name="Ana"):
    return {render(t, name, age) for templates in SUGGESTIONS[language].values() for t in templates if age or not needs_age(t)}


def test_render_replaces_placeholders():
    assert render("Hola {name}, {age} años", "Ana", 30) == "Hola Ana, 30 años"


def test_render_survives_braces_in_the_name():
    assert render("Hola {name}", "{x}") == "Hola {x}"


def test_ordinals():
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 30, 101, 111)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "30th", "101st", "111th"]


# ---------- one kind per message ----------
@pytest.mark.parametrize("language", LANGUAGES)
def test_a_message_is_either_a_greeting_or_a_fact_never_both(language):
    facts = set(facts_for_age(30, language, BORN, TODAY))
    for _ in range(600):
        text = pick(language=language)
        has_fact = any(f in text for f in facts)
        is_greeting = any(g in text for g in greetings(language))
        assert has_fact != is_greeting, text


def test_all_three_kinds_appear():
    kinds = set()
    historical = set(historical_facts(30, "es"))
    calculated = set(messages.calculated_facts(30, "es", BORN, TODAY))
    for _ in range(600):
        text = pick()
        kinds.add("historical" if any(f in text for f in historical) else
                  "calculated" if any(f in text for f in calculated) else "greeting")
    assert kinds == {"greeting", "historical", "calculated"}


def test_kind_proportions_follow_the_weights():
    random.seed(1)
    counts = {"greeting": 0, "fact": 0}
    facts = set(facts_for_age(30, "es", BORN, TODAY))
    for _ in range(2000):
        text = pick()
        counts["fact" if any(f in text for f in facts) else "greeting"] += 1
    assert 0.4 < counts["greeting"] / 2000 < 0.6


def test_unknown_age_only_gives_greetings_without_age_placeholders():
    plain = greetings(age=None)
    for category in CATEGORY_KEYS:
        for _ in range(60):
            text = pick(category=category, age=None)
            assert text in {render(t, "Ana") for t in SUGGESTIONS["es"][category] if not needs_age(t)}
            assert "{" not in text


@pytest.mark.parametrize("category", CATEGORY_KEYS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_every_category_gives_clean_messages(category, language):
    texts = {pick(category, "Ana", 33, language=language) for _ in range(300)}
    assert all("{" not in t and "Ana" in t for t in texts)


def test_unknown_category_falls_back_to_the_generic_one(monkeypatch):
    force_kind(monkeypatch, "greeting")
    assert "Ana" in pick("Inventada")


def test_greeting_kind_mentions_the_age_when_known(monkeypatch):
    force_kind(monkeypatch, "greeting")
    texts = {pick("friends", "Ana", 33) for _ in range(300)}
    assert any("33" in t for t in texts)


# ---------- historical messages: intro + fact + joke ----------
@pytest.mark.parametrize("language", LANGUAGES)
def test_historical_message_has_intro_fact_and_joke(monkeypatch, language):
    force_kind(monkeypatch, "historical")
    entries = historical_entries(35, language)
    for _ in range(100):
        text = pick(age=35, language=language)
        assert any(text == f"{intro.replace('{name}', 'Ana')} {fact} {joke}"
                   for intro in INTROS[language] for fact, joke in entries), text


def test_every_historical_fact_has_a_joke_in_both_languages():
    for entry in FACTS:
        assert len(entry) == 6
        for column in (2, 3, 4, 5):
            assert entry[column].strip()
        assert entry[4] != entry[5] and entry[2] != entry[3]
        assert len(entry[2]) <= MAX_FACT_LENGTH and len(entry[3]) <= MAX_FACT_LENGTH, entry[2]
        assert len(entry[4]) <= MAX_JOKE_LENGTH and len(entry[5]) <= MAX_JOKE_LENGTH, (len(entry[4]), entry[4], len(entry[5]), entry[5])


def test_jokes_have_no_placeholders_and_are_not_repeated_per_fact():
    jokes = [entry[4] for entry in FACTS]
    assert all("{" not in j for j in jokes)
    assert len(set(jokes)) == len(jokes)


# ---------- calculated messages: intro + number + closer ----------
@pytest.mark.parametrize("language", LANGUAGES)
def test_calculated_message_has_intro_fact_and_closer(monkeypatch, language):
    force_kind(monkeypatch, "calculated")
    facts = messages.calculated_facts(30, language, BORN, TODAY)
    for _ in range(100):
        text = pick(language=language)
        assert any(f in text for f in facts)
        assert any(text.startswith(i.replace("{name}", "Ana")) for i in INTROS[language])
        assert any(text.endswith(c) for c in CLOSERS[language])


def test_falls_back_to_a_greeting_when_nothing_else_fits(monkeypatch):
    force_kind(monkeypatch, "historical")
    monkeypatch.setattr(messages, "MAX_MESSAGE_LENGTH", 60)
    monkeypatch.setattr(messages, "historical_entries", lambda age, language: [("x" * 100, "joke")])
    assert pick(age=30) in greetings()


# ---------- length ----------
@pytest.mark.parametrize("language", LANGUAGES)
def test_every_message_fits_the_copy_button_even_with_long_names(language):
    for age in range(1, 101):
        for category in CATEGORY_KEYS:
            for _ in range(6):
                text = pick_suggestion(category, "María Fernanda de los Ángeles", age, "", language,
                                       date(2026 - age, 3, 5), TODAY)
                assert len(text) <= 256, (len(text), text)


# ---------- generate another ----------
@pytest.mark.parametrize("language", LANGUAGES)
def test_generate_another_never_repeats_the_shown_message(language):
    for _ in range(80):
        first = pick(language=language)
        second = pick(previous=first, language=language)
        assert second != first


def test_generate_another_changes_the_fact_not_just_the_intro():
    for _ in range(50):
        first = pick()
        facts = [f for f in facts_for_age(30, "es", BORN, TODAY) if f in first]
        second = pick(previous=first)
        assert not any(f in second for f in facts)


# ---------- age facts ----------
def test_fact_ranges_are_well_formed():
    assert all(entry[0] <= entry[1] for entry in FACTS)


def test_every_age_up_to_99_but_98_has_a_specific_fact():
    gaps = {a for a in range(1, 100) if not any(e[0] == e[1] == a for e in FACTS)}
    assert gaps <= {98}, gaps


def test_facts_have_no_unresolved_placeholders_and_are_short():
    for age in range(1, 121):
        for language in LANGUAGES:
            for fact in facts_for_age(age, language, date(2026 - age, 3, 5), TODAY):
                assert not re.search(r"\{\w+\}", fact), fact
                assert len(fact) <= MAX_FACT_LENGTH, fact


def test_age_specific_facts():
    assert any("Marte" in f for f in historical_facts(2))
    assert not any("Marte" in f for f in historical_facts(5))
    assert any("Bluey" in f for f in historical_facts(30)) and not any("Bluey" in f for f in historical_facts(29))
    assert any("respuesta" in f for f in historical_facts(42))
    assert any("Mozart" in f for f in historical_facts(35))


def test_only_well_known_people_and_nothing_about_recent_tragedies():
    text = " ".join(entry[2] for entry in FACTS)
    for name in ("Báthory", "Heliogábalo", "Tycho", "Schiele", "Albert Fish", "Ceaușescu", "Kobe", "Robin Williams",
                 "Hemingway", "Whitney", "Michael Jackson", "Prince", "Diana"):
        assert name not in text, name

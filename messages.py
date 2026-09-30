import random

from age_facts import calculated_facts, historical_entries
from categories import DEFAULT_CATEGORY
from i18n import DEFAULT_LANGUAGE

# Placeholders: {name} and {age}. Templates with {age} are only used when the birth year is known.
SUGGESTIONS = {
    "es": {
        "friends": [
            "¡Feliz cumple, {name}! 🥳 Que pases un día genial y a ver cuándo lo celebramos con unas cervezas.",
            "¡Felicidades, {name}! 🎉 Un año más viejo, pero igual de inmaduro. ¡Pásalo genial, crack!",
            "¡Muchísimas felicidades, {name}! 🎂 Que este año te traiga tantas alegrías como risas nos hemos echado juntos.",
            "¡{age} añazos, {name}! 🥳 Y lo llevas de maravilla. ¡A celebrarlo por todo lo alto!",
            "¡Feliz cumple, {name}! 🎉 {age} años y cada vez mejor. ¡Brindemos por muchos más!",
            "¡Felicidades, {name}! 🍻 Gracias por ser de esas personas que hacen mejor cualquier plan.",
            "¡Feliz cumple, {name}! 🎈 Hoy mandas tú: elige plan y allí estaremos.",
        ],
        "family": [
            "¡Muchísimas felicidades, {name}! ❤️ Que tengas un día maravilloso. Te mando un abrazo gigante.",
            "¡Feliz cumpleaños, {name}! 🎂 Mis mejores deseos para este nuevo año, disfruta mucho de tu día.",
            "¡Felicidades, {name}! 🥳 Que seas muy feliz hoy y siempre. Te quiero muchísimo.",
            "¡Feliz cumpleaños número {age}, {name}! ❤️ Gracias por todo lo que aportas a la familia. Te quiero.",
            "¡{age} años, {name}! 🎂 Cada año que pasa te quiero más. ¡Que disfrutes muchísimo de tu día!",
            "¡Feliz cumpleaños, {name}! 🏡 Qué suerte tenerte en la familia. Ojalá pronto una buena comida juntos.",
            "¡Felicidades, {name}! 💐 Que este nuevo año venga cargado de salud, alegría y momentos en familia.",
        ],
        "partner": [
            "¡Feliz cumpleaños, {name}! 💕 Eres mi persona favorita del mundo. Hoy y siempre.",
            "¡Felicidades, amor! 🎂 Gracias por cada día a tu lado, {name}. Te quiero muchísimo.",
            "¡Feliz cumple, {name}! 😘 Otro año a tu lado es el mejor regalo que me han hecho.",
            "¡{age} años y cada día más guapo/a, {name}! 💖 Feliz cumpleaños, mi vida.",
            "¡Feliz cumpleaños número {age}, {name}! 🥰 Que todo lo bueno que mereces llegue este año. Te quiero.",
            "¡Felicidades, {name}! 🌹 Hoy toca celebrar a la persona que hace mis días mejores.",
        ],
        "work": [
            "¡Feliz cumpleaños, {name}! 🎂 Que pases un estupendo día. ¡Un saludo!",
            "¡Felicidades en tu día, {name}! 🎉 Te deseo mucho éxito personal y profesional en este nuevo año.",
            "¡Feliz cumpleaños, {name}! 🥂 Que pases un gran día rodeado de los tuyos.",
            "¡Felicidades por tus {age} años, {name}! 🎉 Que sigas cosechando éxitos. ¡Disfruta de tu día!",
            "¡Feliz cumple, {name}! ☕ Que hoy el café y la tarta corran de tu cuenta... o de la nuestra. ¡Disfruta!",
            "¡Feliz cumpleaños, {name}! 🌟 Es un placer trabajar contigo. ¡Que tengas un día estupendo!",
        ],
        "school": [
            "¡Feliz cumple, {name}! 🎓 Que pases un día genial y que hoy no haya deberes ni exámenes.",
            "¡Felicidades, {name}! 🎉 Otro año más de aventuras. ¡Disfruta tu día!",
            "¡Feliz cumpleaños, {name}! 🥳 Qué bien haber coincidido contigo. ¡A celebrarlo!",
            "¡{age} años, {name}! 🎂 Que este año saques matrícula en todo lo que te propongas.",
            "¡Feliz cumple, {name}! 📚 Que se te den bien la vida y las notas. ¡Pásalo genial!",
            "¡Felicidades, {name}! 🎈 Hoy es día de fiesta, ¡los apuntes pueden esperar!",
        ],
        "sports": [
            "¡Feliz cumple, {name}! ⚽ Hoy descansas... pero mañana toca entrenar. ¡Disfruta tu día!",
            "¡Felicidades, {name}! 🏆 Que este año lo ganes todo, dentro y fuera del campo.",
            "¡Feliz cumpleaños, {name}! 🥇 Eres un crack en el equipo. ¡A celebrarlo con unas cañas!",
            "¡{age} años y con esa forma, {name}! 💪 ¡Feliz cumpleaños!",
            "¡Feliz cumple, {name}! 🏃 Que este nuevo año te traiga récords personales y muchas victorias.",
            "¡Felicidades, {name}! 🎉 El tercer tiempo de hoy lo pagas tú... ¡es tu cumple!",
        ],
        "neighbors": [
            "¡Feliz cumpleaños, {name}! 🏠 Es una suerte tenerte de vecino/a. ¡Que pases un día estupendo!",
            "¡Felicidades, {name}! 🎂 Que tengas un día genial. ¡Un abrazo de tu vecino/a!",
            "¡Feliz cumple, {name}! 🎉 Que se te dé todo bien este año. ¡Hasta la escalera!",
            "¡Muchas felicidades por tus {age} años, {name}! 🥳 Que lo disfrutes mucho.",
            "¡Feliz cumpleaños, {name}! 🌷 Gracias por ser tan buena gente. ¡Disfruta de tu día!",
        ],
        "none": [
            "¡Feliz cumpleaños, {name}! 🎂 Que tengas un día estupendo.",
            "¡Felicidades, {name}! 🎉 Te deseo lo mejor en este nuevo año de vida.",
            "¡Muchas felicidades, {name}! 🥳 Que pases un día inolvidable.",
            "¡Feliz cumpleaños número {age}, {name}! 🎂 Que se cumplan todos tus deseos.",
            "¡Felicidades, {name}! 🎈 Que este año venga lleno de cosas buenas.",
            "¡{age} años, {name}! 🥂 Que sean muchos más y todos felices. ¡Feliz cumpleaños!",
        ],
    },
    "en": {
        "friends": [
            "Happy birthday, {name}! 🥳 Have an amazing day, and let's celebrate with a few beers soon.",
            "Happy birthday, {name}! 🎉 One year older, but just as immature. Have a great one, legend!",
            "Happy birthday, {name}! 🎂 May this year bring you as much joy as the laughs we've shared.",
            "{age} and counting, {name}! 🥳 You wear it so well. Let's celebrate big!",
            "Happy birthday, {name}! 🎉 {age} years old and getting better. Cheers to many more!",
            "Happy birthday, {name}! 🍻 Thanks for being one of those people who make any plan better.",
            "Happy birthday, {name}! 🎈 Today you're in charge: pick the plan and we'll be there.",
        ],
        "family": [
            "Happy birthday, {name}! ❤️ Have a wonderful day. Sending you a giant hug.",
            "Happy birthday, {name}! 🎂 My best wishes for this new year, enjoy your day.",
            "Happy birthday, {name}! 🥳 May you be very happy today and always. I love you so much.",
            "Happy {ordinal} birthday, {name}! ❤️ Thank you for everything you bring to the family. Love you.",
            "{age} years old, {name}! 🎂 I love you more with every year. Enjoy your day!",
            "Happy birthday, {name}! 🏡 So lucky to have you in the family. Hoping for a big meal together soon.",
            "Happy birthday, {name}! 💐 May this new year bring health, joy and lots of family moments.",
        ],
        "partner": [
            "Happy birthday, {name}! 💕 You're my favorite person in the world. Today and always.",
            "Happy birthday, love! 🎂 Thank you for every day by your side, {name}. I love you so much.",
            "Happy birthday, {name}! 😘 Another year by your side is the best gift I've ever had.",
            "{age} and more gorgeous every day, {name}! 💖 Happy birthday, my love.",
            "Happy {ordinal} birthday, {name}! 🥰 May everything good you deserve come your way this year. I love you.",
            "Happy birthday, {name}! 🌹 Today we celebrate the person who makes my days better.",
        ],
        "work": [
            "Happy birthday, {name}! 🎂 Have a great day. Best wishes!",
            "Happy birthday, {name}! 🎉 Wishing you lots of personal and professional success this year.",
            "Happy birthday, {name}! 🥂 Have a great day surrounded by your loved ones.",
            "Happy {ordinal} birthday, {name}! 🎉 Keep on succeeding. Enjoy your day!",
            "Happy birthday, {name}! ☕ Today the coffee and cake are on you... or on us. Enjoy!",
            "Happy birthday, {name}! 🌟 It's a pleasure working with you. Have a great day!",
        ],
        "school": [
            "Happy birthday, {name}! 🎓 Have a great day, with no homework or exams today.",
            "Happy birthday, {name}! 🎉 Another year of adventures. Enjoy your day!",
            "Happy birthday, {name}! 🥳 So glad we met. Let's celebrate!",
            "{age} years old, {name}! 🎂 May you ace everything you set your mind to this year.",
            "Happy birthday, {name}! 📚 May life and grades both go well. Have a blast!",
            "Happy birthday, {name}! 🎈 Today is a party day, the notes can wait!",
        ],
        "sports": [
            "Happy birthday, {name}! ⚽ Rest today... but training is back tomorrow. Enjoy your day!",
            "Happy birthday, {name}! 🏆 May you win everything this year, on and off the field.",
            "Happy birthday, {name}! 🥇 You're a star of the team. Let's celebrate with a few drinks!",
            "{age} years old and in that shape, {name}! 💪 Happy birthday!",
            "Happy birthday, {name}! 🏃 May this new year bring personal bests and lots of wins.",
            "Happy birthday, {name}! 🎉 The post-game round is on you today... it's your birthday!",
        ],
        "neighbors": [
            "Happy birthday, {name}! 🏠 We're lucky to have you as a neighbor. Have a great day!",
            "Happy birthday, {name}! 🎂 Have a wonderful day. A hug from your neighbor!",
            "Happy birthday, {name}! 🎉 May everything go well this year. See you in the hallway!",
            "Happy {ordinal} birthday, {name}! 🥳 Enjoy it!",
            "Happy birthday, {name}! 🌷 Thanks for being such a good person. Enjoy your day!",
        ],
        "none": [
            "Happy birthday, {name}! 🎂 Have a great day.",
            "Happy birthday, {name}! 🎉 Wishing you the best in this new year of life.",
            "Happy birthday, {name}! 🥳 Have an unforgettable day.",
            "Happy {ordinal} birthday, {name}! 🎂 May all your wishes come true.",
            "Happy birthday, {name}! 🎈 May this year be full of good things.",
            "{age} years old, {name}! 🥂 May there be many more, all happy ones. Happy birthday!",
        ],
    },
}

# A message is ONE of these kinds (never a mix):
#   greeting   - a greeting written for the contact's category
#   historical - intro + something a famous person did at that age + a joke about it
#   calculated - intro + a number worked out from the birth date + a closing remark
# The last two need a known birth year.
KIND_WEIGHTS = {"greeting": 0.5, "historical": 0.25, "calculated": 0.25}
MAX_MESSAGE_LENGTH = 256

INTROS = {
    "es": ["¡Feliz cumple, {name}!", "¡Felicidades, {name}!", "¡Feliz cumpleaños, {name}!"],
    "en": ["Happy birthday, {name}!", "Congrats, {name}!", "Happy birthday to you, {name}!"],
}
CLOSERS = {
    "es": ["¡Y todavía te quedan muchos más!", "Y eso sin contar las siestas.", "¡Qué cantidad de tarta acumulada!",
           "Da para mucha fiesta.", "¡A celebrarlo por todo lo alto!"],
    "en": ["And you've got plenty more to go!", "And that's without counting naps.", "That's a lot of accumulated cake!",
           "Plenty of reasons to party.", "Let's celebrate big!"],
}


def ordinal(number):
    """1 -> '1st', 12 -> '12th', 23 -> '23rd'"""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def needs_age(template):
    return "{age}" in template or "{ordinal}" in template


def render(template, name, age=None):
    text = template.replace("{name}", name)
    if age is not None:
        text = text.replace("{age}", str(age)).replace("{ordinal}", ordinal(age))
    return text


def _fresh(options, previous_text):
    """Options not already shown in `previous_text` (all of them if every one was)."""
    if not previous_text:
        return options
    return [o for o in options if o not in previous_text] or options


def _fits(text):
    return len(text) <= MAX_MESSAGE_LENGTH


def _greeting(category, name, age, previous_text, language):
    catalog = SUGGESTIONS.get(language, SUGGESTIONS[DEFAULT_LANGUAGE])
    templates = catalog.get(category, catalog[DEFAULT_CATEGORY])
    options = [render(t, name, age) for t in templates if age is not None or not needs_age(t)]
    return random.choice(_fresh(options, previous_text))


def _historical(name, age, previous_text, language):
    intros = INTROS.get(language, INTROS[DEFAULT_LANGUAGE])
    options = []
    for fact, joke in historical_entries(age, language):
        for intro in intros:
            text = f"{render(intro, name)} {fact} {joke}"
            if _fits(text):
                options.append((fact, text))
    if not options:
        return None
    fresh = _fresh([fact for fact, _ in options], previous_text)
    return random.choice([text for fact, text in options if fact in fresh])


def _calculated(name, age, previous_text, language, birth_date, today):
    intros = INTROS.get(language, INTROS[DEFAULT_LANGUAGE])
    closers = CLOSERS.get(language, CLOSERS[DEFAULT_LANGUAGE])
    options = []
    for fact in calculated_facts(age, language, birth_date, today):
        text = f"{render(random.choice(intros), name)} {fact} {random.choice(closers)}"
        if _fits(text):
            options.append((fact, text))
    if not options:
        return None
    fresh = _fresh([fact for fact, _ in options], previous_text)
    return random.choice([text for fact, text in options if fact in fresh])


def pick_suggestion(category, name, age=None, previous_text="", language=DEFAULT_LANGUAGE, birth_date=None, today=None):
    """One message for the contact: a category greeting, a famous-people fact with a joke, or a calculated fact.

    Kinds are drawn with KIND_WEIGHTS; if the drawn kind has nothing to offer (unknown age, no fact fits...)
    another one is used. `previous_text` is the message already shown, so "generate another" doesn't repeat it.
    """
    kinds = [k for k, weight in KIND_WEIGHTS.items() if weight > 0 and (age or k == "greeting")]
    order = []
    while kinds:
        kind = random.choices(kinds, weights=[KIND_WEIGHTS[k] for k in kinds])[0]
        order.append(kind)
        kinds.remove(kind)
    for kind in order:
        if kind == "greeting":
            return _greeting(category, name, age, previous_text, language)
        if kind == "historical":
            text = _historical(name, age, previous_text, language)
        else:
            text = _calculated(name, age, previous_text, language, birth_date, today)
        if text:
            return text
    return _greeting(category, name, age, previous_text, language)

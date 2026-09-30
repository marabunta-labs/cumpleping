"""User-facing texts in every supported language, and language detection."""

SUPPORTED_LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "es"
FALLBACK_LANGUAGE = "en"  # used for detected languages we don't translate (fr, de, pt...)
LANGUAGE_NAMES = {"es": "Español", "en": "English"}


def detect_language(language_code):
    """Map Telegram's `language_code` (e.g. 'es', 'es-MX', 'en-GB', None) to a supported language."""
    if not isinstance(language_code, str) or not language_code:
        return DEFAULT_LANGUAGE
    base = language_code.lower().replace("_", "-").split("-")[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    return FALLBACK_LANGUAGE


def normalize_language(language):
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


STRINGS = {
    "es": {
        "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                   "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        "date_format": "{day} de {month}",
        "csv_headers": ['Nombre', 'Fecha', 'Año', 'Categoría', 'Teléfono'],
        "csv_filename": "mis_cumpleaños.csv",
        # --- start / help ---
        "start_greeting": "¡Hola! Soy Cumpleping 🎂.\nTe ayudaré a recordar cumpleaños y a felicitar a tu gente.\nUsa /nuevo, /listar, /ajustes o /ayuda.",
        "zone_prompt_start": "🌍 Para avisarte a tu hora local, ¿en qué zona horaria estás?\n(Puedes cambiarlo luego en /ajustes)",
        "help_text": ("🎂 <b>Cumpleping</b> te recuerda los cumpleaños y te prepara la felicitación.\n\n"
                      "/nuevo – Añadir un cumpleaños\n/listar – Ver, editar o borrar cumpleaños\n"
                      "/ajustes – Hora del aviso, zona horaria e idioma\n"
                      "/zona – Cambiar la zona horaria escribiendo su nombre (ej. <code>/zona Europe/Paris</code>)\n"
                      "/idioma – Cambiar el idioma\n/exportar – Descargar una copia de seguridad (CSV)\n"
                      "/cancelar – Cancelar lo que estás haciendo"),
        "stray_text": "No te he entendido 🤔. Usa /nuevo para añadir un cumpleaños o /ayuda para ver las opciones.",
        "btn_add_birthday": "➕ Añadir Cumpleaños",
        "btn_view_birthdays": "🗂️ Ver mis cumpleaños",
        # --- create ---
        "new_ask_name": "¡Vamos a añadir un cumpleaños! 🎂\n\n¿De quién es? (Escribe solo el nombre)\n\nPuedes salir cuando quieras con /cancelar",
        "name_invalid": "El nombre debe tener entre 1 y 50 caracteres. Prueba otra vez:",
        "name_saved": "Guardaré a {name}.\n\n¿En qué mes nació?",
        "ask_day": "Genial. ¿Qué día?",
        "ask_year": "Fecha: {date}.\n\n¿Sabes en qué año nació? (así podré decirte cuántos años cumple)",
        "btn_yes_know": "Sí, lo sé",
        "btn_no_skip": "No, saltar",
        "pick_year": "Selecciona el año o escríbelo (ej. 1995):",
        "year_leap_alert": "El 29 de febrero solo existe en años bisiestos. Elige otro año.",
        "year_leap_text": "El 29 de febrero solo existe en años bisiestos. Prueba con otro año.",
        "year_invalid": "Escribe un año de 4 cifras válido (ej. 1995) o elige uno de los botones.",
        "ask_category": "¿En qué categoría lo guardamos?",
        "ask_phone": "¿Quieres añadir su teléfono para enviarle la felicitación por WhatsApp/Telegram?",
        "btn_add_number": "Sí, añadir número",
        "btn_finish": "No, terminar",
        "keypad_text": "Usa el teclado, escríbelo (con prefijo) o comparte un contacto 📎:\n\n📱 Número: <code>{number}</code>",
        "btn_done": "✅ Listo",
        "btn_skip": "⏭️ Saltar",
        "phone_incomplete": "El número parece incompleto. Revísalo o pulsa Saltar.",
        "contact_invalid": "Ese contacto no tiene un teléfono válido. Prueba con otro o escríbelo.",
        "phone_invalid": "Ese número no parece válido (entre 8 y 15 dígitos, con prefijo de país). Inténtalo de nuevo.",
        "saved_summary": "✅ ¡Guardado con éxito!\n\n👤 {name}\n📅 {date}\n🏷️ {category}",
        "saved_born": "\n🗓️ Nació en {year}",
        "btn_add_another": "➕ Añadir otro",
        "cancelled": "❌ Cancelado. Cuando quieras, usa /nuevo o /listar.",
        # --- list ---
        "list_ask": "¿Qué cumpleaños quieres consultar?",
        "btn_upcoming": "📅 Próximos 30 días",
        "btn_this_month": "🗓️ Este mes",
        "btn_all": "🗂️ Todos",
        "btn_back": "🔙 Volver",
        "list_none": "No tienes cumpleaños guardados. ¡Usa /nuevo!",
        "list_empty_filter": "No hay cumpleaños en este filtro.",
        "title_upcoming": "📅 <b>Próximos 30 días</b>",
        "title_month": "🗓️ <b>Cumpleaños de {month}</b>",
        "title_all": "🗂️ <b>Todos tus cumpleaños</b>",
        "list_hint": "Toca un nombre para verlo, editarlo o borrarlo:",
        "label_today": "¡ES HOY!",
        "label_tomorrow": "mañana",
        "label_in_days": "en {n}d",
        "label_age": " · {n} años",
        # --- profile / delete ---
        "profile_text": "👤 <b>Perfil de {name}</b>\n\n📅 Fecha: {date}\n{year_line}\n🏷️ Categoría: {category}\n📱 Teléfono: {phone}",
        "profile_year": "🗓️ Año: {year}",
        "profile_will_turn": " (cumplirá {age})",
        "profile_year_unknown": "🗓️ Año: no indicado",
        "profile_no_phone": "No guardado",
        "btn_edit": "✏️ Editar",
        "btn_delete": "🗑️ Borrar",
        "btn_back_to_list": "🔙 Volver a la lista",
        "profile_not_found": "❌ Perfil no encontrado.",
        "confirm_delete": "¿Seguro que quieres borrar a <b>{name}</b>?",
        "btn_yes_delete": "🗑️ Sí, borrar",
        "btn_no": "↩️ No",
        "deleted": "🗑️ Cumpleaños eliminado.",
        "already_gone": "❌ Ese cumpleaños ya no existe.",
        # --- edit ---
        "edit_what": "✏️ ¿Qué quieres editar de <b>{name}</b>?",
        "btn_field_name": "👤 Nombre",
        "btn_field_date": "📅 Fecha",
        "btn_field_year": "🗓️ Año",
        "btn_field_category": "🏷️ Categoría",
        "btn_field_phone": "📱 Teléfono",
        "btn_cancel": "🔙 Cancelar",
        "edit_cancelled": "Edición cancelada.",
        "edit_ask_name": "Escribe el nuevo nombre (o /cancelar):",
        "edit_ask_month": "¿En qué mes es el cumpleaños?",
        "edit_ask_year": "Selecciona el año, escríbelo (ej. 1995) o marca desconocido:",
        "edit_ask_category": "Elige la nueva categoría:",
        "edit_ask_phone": "Escribe el nuevo teléfono con prefijo (ej. +34600111222), comparte un contacto 📎 o pulsa Quitar:",
        "btn_remove_phone": "🚫 Quitar teléfono",
        "btn_unknown_year": "❓ Desconocido",
        "changes_saved": "✅ Cambios guardados.",
        "edit_leap_alert": "{name} nació en {year} (no bisiesto): no puede cumplir el 29 de febrero. Cambia antes el año.",
        # --- settings ---
        "settings_text": ("⚙️ <b>Ajustes</b>\n\n🕐 Hora del aviso: <b>{hour}</b>\n"
                          "🌍 Zona horaria: <b>{zone}</b> (ahora allí son las {time})\n🌐 Idioma: <b>{language_name}</b>\n\n"
                          "Te avisaré cada cumpleaños a esa hora, en tu hora local."),
        "btn_change_hour": "🕐 Cambiar hora",
        "btn_change_zone": "🌍 Cambiar zona",
        "btn_change_language": "🌐 Idioma",
        "choose_hour": "¿A qué hora quieres que te avise? (hora local de tu zona)",
        "choose_zone": "¿En qué zona horaria estás?\n\nSi no aparece la tuya, usa <code>/zona Nombre/Ciudad</code> (ej. <code>/zona Europe/Paris</code>).",
        "hour_saved": "✅ ¡Hecho! Te avisaré de los cumpleaños a las {hour} ({zone}).",
        "zone_saved": "✅ Zona horaria: <b>{zone}</b>.\nTe avisaré a las {hour} de tu hora local (cámbialo en /ajustes).",
        "zone_invalid": "❌ Zona horaria no válida.",
        "zone_pick": "Elige tu zona horaria:",
        "zone_unknown": "No conozco esa zona 🤔. Usa el formato Continente/Ciudad, por ejemplo <code>/zona America/Bogota</code>.",
        "zone_cmd_saved": "✅ Zona horaria guardada: {zone}",
        "choose_language": "🌐 Elige el idioma:",
        "language_saved": "✅ Idioma: Español",
        # --- export ---
        "export_none": "No tienes cumpleaños guardados para exportar.",
        "export_caption": "📊 Aquí tienes la copia de seguridad.",
        # --- reminder ---
        "reminder_title": "🔔 <b>¡RECORDATORIO DE CUMPLEAÑOS!</b>\n\n",
        "reminder_today": "Hoy es el cumpleaños de <b>{name}</b>",
        "reminder_age": " ({age} años) 🎂\n",
        "reminder_no_age": " 🎂\n",
        "reminder_suggestion": "\n💡 <b>Sugerencia:</b>\n{idea}\n",
        "btn_copy": "📋 Copiar mensaje",
        "btn_another": "🔄 Generar otro",
        "btn_share_tg": "🔵 Compartir TG",
        "birthday_gone": "Este cumpleaños ya no existe.",
        "error_generic": "⚠️ Algo salió mal. Inténtalo de nuevo con /nuevo o /listar.",
    },
    "en": {
        "months": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "date_format": "{month} {day}",
        "csv_headers": ['Name', 'Date', 'Year', 'Category', 'Phone'],
        "csv_filename": "my_birthdays.csv",
        "start_greeting": "Hi! I'm Cumpleping 🎂.\nI'll help you remember birthdays and greet your people.\nUse /new, /list, /settings or /help.",
        "zone_prompt_start": "🌍 To remind you at your local time, which time zone are you in?\n(You can change it later in /settings)",
        "help_text": ("🎂 <b>Cumpleping</b> reminds you of birthdays and prepares the greeting.\n\n"
                      "/new – Add a birthday\n/list – View, edit or delete birthdays\n"
                      "/settings – Reminder hour, time zone and language\n"
                      "/timezone – Change the time zone by typing its name (e.g. <code>/timezone Europe/Paris</code>)\n"
                      "/language – Change the language\n/export – Download a backup (CSV)\n"
                      "/cancel – Cancel what you are doing"),
        "stray_text": "I didn't understand 🤔. Use /new to add a birthday or /help to see the options.",
        "btn_add_birthday": "➕ Add birthday",
        "btn_view_birthdays": "🗂️ View my birthdays",
        "new_ask_name": "Let's add a birthday! 🎂\n\nWhose is it? (Just type the name)\n\nYou can leave anytime with /cancel",
        "name_invalid": "The name must be between 1 and 50 characters. Try again:",
        "name_saved": "I'll save {name}.\n\nWhich month were they born in?",
        "ask_day": "Great. Which day?",
        "ask_year": "Date: {date}.\n\nDo you know the year they were born? (so I can tell you how old they turn)",
        "btn_yes_know": "Yes, I do",
        "btn_no_skip": "No, skip",
        "pick_year": "Pick the year or type it (e.g. 1995):",
        "year_leap_alert": "February 29 only exists in leap years. Pick another year.",
        "year_leap_text": "February 29 only exists in leap years. Try another year.",
        "year_invalid": "Type a valid 4-digit year (e.g. 1995) or pick one of the buttons.",
        "ask_category": "Which category should I save it in?",
        "ask_phone": "Do you want to add their phone to send the greeting via WhatsApp/Telegram?",
        "btn_add_number": "Yes, add number",
        "btn_finish": "No, finish",
        "keypad_text": "Use the keypad, type it (with country code) or share a contact 📎:\n\n📱 Number: <code>{number}</code>",
        "btn_done": "✅ Done",
        "btn_skip": "⏭️ Skip",
        "phone_incomplete": "The number looks incomplete. Check it or press Skip.",
        "contact_invalid": "That contact has no valid phone. Try another one or type it.",
        "phone_invalid": "That number doesn't look valid (8 to 15 digits, with country code). Try again.",
        "saved_summary": "✅ Saved!\n\n👤 {name}\n📅 {date}\n🏷️ {category}",
        "saved_born": "\n🗓️ Born in {year}",
        "btn_add_another": "➕ Add another",
        "cancelled": "❌ Cancelled. Whenever you want, use /new or /list.",
        "list_ask": "Which birthdays do you want to see?",
        "btn_upcoming": "📅 Next 30 days",
        "btn_this_month": "🗓️ This month",
        "btn_all": "🗂️ All",
        "btn_back": "🔙 Back",
        "list_none": "You have no saved birthdays. Use /new!",
        "list_empty_filter": "There are no birthdays in this filter.",
        "title_upcoming": "📅 <b>Next 30 days</b>",
        "title_month": "🗓️ <b>Birthdays in {month}</b>",
        "title_all": "🗂️ <b>All your birthdays</b>",
        "list_hint": "Tap a name to view, edit or delete it:",
        "label_today": "TODAY!",
        "label_tomorrow": "tomorrow",
        "label_in_days": "in {n}d",
        "label_age": " · {n} years",
        "profile_text": "👤 <b>{name}'s profile</b>\n\n📅 Date: {date}\n{year_line}\n🏷️ Category: {category}\n📱 Phone: {phone}",
        "profile_year": "🗓️ Year: {year}",
        "profile_will_turn": " (turning {age})",
        "profile_year_unknown": "🗓️ Year: not provided",
        "profile_no_phone": "Not saved",
        "btn_edit": "✏️ Edit",
        "btn_delete": "🗑️ Delete",
        "btn_back_to_list": "🔙 Back to list",
        "profile_not_found": "❌ Profile not found.",
        "confirm_delete": "Are you sure you want to delete <b>{name}</b>?",
        "btn_yes_delete": "🗑️ Yes, delete",
        "btn_no": "↩️ No",
        "deleted": "🗑️ Birthday deleted.",
        "already_gone": "❌ That birthday no longer exists.",
        "edit_what": "✏️ What do you want to edit for <b>{name}</b>?",
        "btn_field_name": "👤 Name",
        "btn_field_date": "📅 Date",
        "btn_field_year": "🗓️ Year",
        "btn_field_category": "🏷️ Category",
        "btn_field_phone": "📱 Phone",
        "btn_cancel": "🔙 Cancel",
        "edit_cancelled": "Edit cancelled.",
        "edit_ask_name": "Type the new name (or /cancel):",
        "edit_ask_month": "Which month is the birthday in?",
        "edit_ask_year": "Pick the year, type it (e.g. 1995) or mark unknown:",
        "edit_ask_category": "Pick the new category:",
        "edit_ask_phone": "Type the new phone with country code (e.g. +34600111222), share a contact 📎 or press Remove:",
        "btn_remove_phone": "🚫 Remove phone",
        "btn_unknown_year": "❓ Unknown",
        "changes_saved": "✅ Changes saved.",
        "edit_leap_alert": "{name} was born in {year} (not a leap year): they can't have a Feb 29 birthday. Change the year first.",
        "settings_text": ("⚙️ <b>Settings</b>\n\n🕐 Reminder hour: <b>{hour}</b>\n"
                          "🌍 Time zone: <b>{zone}</b> (it is {time} there now)\n🌐 Language: <b>{language_name}</b>\n\n"
                          "I'll remind you of every birthday at that hour, in your local time."),
        "btn_change_hour": "🕐 Change hour",
        "btn_change_zone": "🌍 Change zone",
        "btn_change_language": "🌐 Language",
        "choose_hour": "At what hour should I remind you? (local time of your zone)",
        "choose_zone": "Which time zone are you in?\n\nIf yours isn't listed, use <code>/timezone Region/City</code> (e.g. <code>/timezone Europe/Paris</code>).",
        "hour_saved": "✅ Done! I'll remind you of birthdays at {hour} ({zone}).",
        "zone_saved": "✅ Time zone: <b>{zone}</b>.\nI'll remind you at {hour} your local time (change it in /settings).",
        "zone_invalid": "❌ Invalid time zone.",
        "zone_pick": "Pick your time zone:",
        "zone_unknown": "I don't know that zone 🤔. Use the Region/City format, e.g. <code>/timezone America/Bogota</code>.",
        "zone_cmd_saved": "✅ Time zone saved: {zone}",
        "choose_language": "🌐 Choose the language:",
        "language_saved": "✅ Language: English",
        "export_none": "You have no saved birthdays to export.",
        "export_caption": "📊 Here is your backup.",
        "reminder_title": "🔔 <b>BIRTHDAY REMINDER!</b>\n\n",
        "reminder_today": "Today is <b>{name}</b>'s birthday",
        "reminder_age": " ({age} years old) 🎂\n",
        "reminder_no_age": " 🎂\n",
        "reminder_suggestion": "\n💡 <b>Suggestion:</b>\n{idea}\n",
        "btn_copy": "📋 Copy message",
        "btn_another": "🔄 Another one",
        "btn_share_tg": "🔵 Share on TG",
        "birthday_gone": "This birthday no longer exists.",
        "error_generic": "⚠️ Something went wrong. Try again with /new or /list.",
    },
}

COMMAND_DESCRIPTIONS = {
    "es": [("nuevo", "Añadir un cumpleaños"), ("listar", "Ver, editar o borrar cumpleaños"),
           ("ajustes", "Hora del aviso, zona horaria e idioma"), ("exportar", "Descargar copia de seguridad (CSV)"),
           ("cancelar", "Cancelar lo que estoy haciendo"), ("ayuda", "Ver la ayuda")],
    "en": [("new", "Add a birthday"), ("list", "View, edit or delete birthdays"),
           ("settings", "Reminder hour, time zone and language"), ("export", "Download a backup (CSV)"),
           ("cancel", "Cancel what I'm doing"), ("help", "Show help")],
}


def t(language, key, **values):
    """Text for `key` in `language` (Spanish if the key is missing there), formatted with `values`."""
    catalog = STRINGS.get(language) or STRINGS[DEFAULT_LANGUAGE]
    text = catalog[key] if key in catalog else STRINGS[DEFAULT_LANGUAGE][key]
    if values and isinstance(text, str):
        return text.format(**values)
    return text

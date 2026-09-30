import os
import urllib.parse
import csv
import io
import pytz
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest
from datetime import datetime
import random
from database import *
from mensajes import SUGERENCIAS

NOMBRE, MES, DIA, PREGUNTA_ANIO, SELECCIONAR_ANIO, CATEGORIA, PREGUNTA_TELEFONO, RECIBIR_TELEFONO = range(8)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- BÁSICOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("➕ Añadir Cumpleaños", callback_data="start_nuevo")],
        [InlineKeyboardButton("🗂️ Ver mis cumpleaños", callback_data="start_listar")]
    ]
    await update.message.reply_text(
        "¡Hola! Soy Cumpleping 🎂.\nTe ayudaré a recordar todos los cumpleaños y te sugeriré cómo felicitarlos.\n\nUsa el menú o los comandos como /nuevo, /listar o /ajustes.",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# --- FLUJO DE CREACIÓN ---
async def nuevo_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.callback_query.message if update.callback_query else update.message
    if update.callback_query: await update.callback_query.answer()
    await mensaje.reply_text("¡Vamos a añadir un cumpleaños! 🎂\n\n¿De quién es el cumpleaños? (Escribe solo el nombre)")
    return NOMBRE

async def nuevo_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nombre'] = update.message.text
    teclado = [
        [InlineKeyboardButton("Enero", callback_data="mes_01"), InlineKeyboardButton("Febrero", callback_data="mes_02"), InlineKeyboardButton("Marzo", callback_data="mes_03")],
        [InlineKeyboardButton("Abril", callback_data="mes_04"), InlineKeyboardButton("Mayo", callback_data="mes_05"), InlineKeyboardButton("Junio", callback_data="mes_06")],
        [InlineKeyboardButton("Julio", callback_data="mes_07"), InlineKeyboardButton("Agosto", callback_data="mes_08"), InlineKeyboardButton("Septiembre", callback_data="mes_09")],
        [InlineKeyboardButton("Octubre", callback_data="mes_10"), InlineKeyboardButton("Noviembre", callback_data="mes_11"), InlineKeyboardButton("Diciembre", callback_data="mes_12")]
    ]
    await update.message.reply_text(f"Guardaré a {context.user_data['nombre']}.\n\n¿En qué mes nació?", reply_markup=InlineKeyboardMarkup(teclado))
    return MES

async def recibir_mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mes = query.data.split('_')[1] 
    context.user_data['mes'] = mes
    max_dias = 31 if mes in ['01', '03', '05', '07', '08', '10', '12'] else (30 if mes in ['04', '06', '09', '11'] else 29)
    botones_dias = []
    fila = []
    for i in range(1, max_dias + 1):
        fila.append(InlineKeyboardButton(str(i), callback_data=f"dia_{i:02d}"))
        if len(fila) == 7:
            botones_dias.append(fila)
            fila = []
    if fila: botones_dias.append(fila)
    await query.edit_message_text(text="Genial. ¿Qué día?", reply_markup=InlineKeyboardMarkup(botones_dias))
    return DIA

async def recibir_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dia = query.data.split('_')[1]
    context.user_data['fecha'] = f"{dia}/{context.user_data['mes']}" 
    teclado = [[InlineKeyboardButton("Sí, lo sé", callback_data="si_anio")], [InlineKeyboardButton("No, saltar", callback_data="no_anio")]]
    await query.edit_message_text(text=f"Fecha: {dia}/{context.user_data['mes']}.\n\n¿Sabes en qué año nació?", reply_markup=InlineKeyboardMarkup(teclado))
    return PREGUNTA_ANIO

def generar_teclado_anios(año_inicio):
    botones, fila = [], []
    for i in range(12): 
        año_actual = año_inicio + i
        fila.append(InlineKeyboardButton(str(año_actual), callback_data=f"anio_{año_actual}"))
        if len(fila) == 3:
            botones.append(fila)
            fila = []
    botones.append([InlineKeyboardButton("⬅️", callback_data=f"nav_anio_{año_inicio - 12}"), InlineKeyboardButton("➡️", callback_data=f"nav_anio_{año_inicio + 12}")])
    return InlineKeyboardMarkup(botones)

async def preguntar_anio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    if query.data == "si_anio":
        await query.edit_message_text(text="Selecciona el año:", reply_markup=generar_teclado_anios(1990))
        return SELECCIONAR_ANIO
    else:
        context.user_data['anio'] = "Desconocido"
        return await mostrar_teclado_categoria(query)

async def navegar_anios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=generar_teclado_anios(int(query.data.split('_')[2])))
    return SELECCIONAR_ANIO

async def recibir_anio_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['anio'] = query.data.split('_')[1]
    return await mostrar_teclado_categoria(query)

async def mostrar_teclado_categoria(mensaje_o_query):
    teclado = [[InlineKeyboardButton("👨‍👩‍👧 Familia", callback_data="Familia"), InlineKeyboardButton("🍻 Amigos", callback_data="Amigos")],
               [InlineKeyboardButton("💼 Trabajo", callback_data="Trabajo"), InlineKeyboardButton("🤷 Ninguna", callback_data="Ninguna")]]
    texto = "¿En qué categoría lo guardamos?"
    try: await mensaje_o_query.edit_message_text(text=texto, reply_markup=InlineKeyboardMarkup(teclado))
    except: await mensaje_o_query.reply_text(text=texto, reply_markup=InlineKeyboardMarkup(teclado))
    return CATEGORIA

async def recibir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['categoria'] = query.data
    teclado = [[InlineKeyboardButton("Sí, añadir número", callback_data="si_tel")], [InlineKeyboardButton("No, terminar", callback_data="no_tel")]]
    await query.edit_message_text("¿Quieres añadir su teléfono para enviarle mensajes directos?", reply_markup=InlineKeyboardMarkup(teclado))
    return PREGUNTA_TELEFONO

def generar_teclado_numpad():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data="num_1"), InlineKeyboardButton("2", callback_data="num_2"), InlineKeyboardButton("3", callback_data="num_3")],
        [InlineKeyboardButton("4", callback_data="num_4"), InlineKeyboardButton("5", callback_data="num_5"), InlineKeyboardButton("6", callback_data="num_6")],
        [InlineKeyboardButton("7", callback_data="num_7"), InlineKeyboardButton("8", callback_data="num_8"), InlineKeyboardButton("9", callback_data="num_9")],
        [InlineKeyboardButton("+", callback_data="num_+"), InlineKeyboardButton("0", callback_data="num_0"), InlineKeyboardButton("⌫", callback_data="num_del")],
        [InlineKeyboardButton("✅ Listo", callback_data="num_listo")]
    ])

async def preguntar_telefono_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "si_tel":
        context.user_data['telefono_temp'] = "+34"
        texto = f"Usa el teclado, escríbelo o **comparte un contacto** 📎:\n\n📱 Número: `{context.user_data['telefono_temp']}`"
        await query.edit_message_text(text=texto, reply_markup=generar_teclado_numpad(), parse_mode="Markdown")
        return RECIBIR_TELEFONO
    else:
        context.user_data['telefono'] = ""
        return await guardar_y_terminar(query, context)

async def manejar_teclado_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion = query.data.split('_')[1]
    
    if accion == "listo":
        context.user_data['telefono'] = context.user_data['telefono_temp'].replace("+", "").replace(" ", "")
        return await guardar_y_terminar(query, context)
    elif accion == "del":
        context.user_data['telefono_temp'] = context.user_data['telefono_temp'][:-1]
    else:
        context.user_data['telefono_temp'] += accion
        
    texto = f"Usa el teclado, escríbelo o **comparte un contacto** 📎:\n\n📱 Número: `{context.user_data['telefono_temp']}`"
    await query.edit_message_text(text=texto, reply_markup=generar_teclado_numpad(), parse_mode="Markdown")
    return RECIBIR_TELEFONO

async def recibir_contacto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['telefono'] = update.message.contact.phone_number.replace("+", "").replace(" ", "").replace("-", "")
    return await guardar_y_terminar(update.message, context)

async def recibir_telefono_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['telefono'] = update.message.text.replace("+", "").replace(" ", "")
    return await guardar_y_terminar(update.message, context)

async def guardar_y_terminar(mensaje_o_query, context):
    try: chat_id = mensaje_o_query.message.chat_id
    except: chat_id = mensaje_o_query.chat_id 
    agregar_cumple(chat_id, context.user_data['nombre'], context.user_data['fecha'], context.user_data['anio'], context.user_data['categoria'], context.user_data['telefono'])
    
    resumen = f"✅ ¡Guardado con éxito!\n\n👤 {context.user_data['nombre']}\n📅 {context.user_data['fecha']}"
    try: await mensaje_o_query.edit_message_text(text=resumen)
    except: await mensaje_o_query.reply_text(text=resumen)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Creación cancelada.")
    return ConversationHandler.END


# --- MENÚ LISTAR Y CONSULTAS ---
async def listar_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.callback_query.message if update.callback_query else update.message
    if update.callback_query: await update.callback_query.answer()
    
    teclado = [
        [InlineKeyboardButton("📅 Próximos 30 días", callback_data="list_proximos")],
        [InlineKeyboardButton("🗓️ Este mes", callback_data="list_mes")],
        [InlineKeyboardButton("🗂️ Todos", callback_data="list_todos")]
    ]
    await mensaje.reply_text("¿Qué cumpleaños quieres consultar?", reply_markup=InlineKeyboardMarkup(teclado))

async def manejar_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filtro = query.data.split('_')[1]
    
    cumples = obtener_cumples_por_usuario(query.message.chat_id)
    if not cumples:
        return await query.edit_message_text("No tienes ningún cumpleaños guardado. ¡Usa /nuevo!")
        
    hoy = datetime.now()
    hoy_solo_fecha = datetime(hoy.year, hoy.month, hoy.day)
    
    def dias_faltan(fecha_str):
        dia, mes = int(fecha_str.split('/')[0]), int(fecha_str.split('/')[1])
        cumple = datetime(hoy.year, mes, dia)
        if cumple < hoy_solo_fecha:
            cumple = datetime(hoy.year + 1, mes, dia)
        return (cumple - hoy_solo_fecha).days

    cumples_ordenados = sorted(cumples, key=lambda x: dias_faltan(x[2]))
    
    if filtro == "proximos":
        filtrados = [c for c in cumples_ordenados if dias_faltan(c[2]) <= 30]
        titulo = "📅 *Próximos 30 días:*\n\nToca un nombre para gestionarlo:"
    elif filtro == "mes":
        filtrados = [c for c in cumples_ordenados if c[2].split('/')[1] == hoy.strftime("%m")]
        titulo = f"🗓️ *Cumpleaños de este mes:*\n\nToca un nombre para gestionarlo:"
    else:
        filtrados = cumples_ordenados
        titulo = "🗂️ *Todos tus cumpleaños:*\n\nToca un nombre para gestionarlo:"

    if not filtrados:
        await query.edit_message_text("No hay cumpleaños en este filtro. 🏖️️", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="list_volver")]]))
        return

    # NUEVO: Convertimos la lista de texto en botones interactivos
    teclado = []
    for c in filtrados:
        id_bd, nombre, fecha = c[0], c[1], c[2]
        faltan = dias_faltan(fecha)
        texto_dias = "¡ES HOY!" if faltan == 0 else ("Mañana" if faltan == 1 else f"en {faltan}d")
        teclado.append([InlineKeyboardButton(f"{nombre} - {fecha} ({texto_dias})", callback_data=f"ver_{id_bd}")])
    
    teclado.append([InlineKeyboardButton("🔙 Volver", callback_data="list_volver")])
    await query.edit_message_text(text=titulo, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(teclado))

async def ver_perfil_cumple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    id_cumple = int(query.data.split('_')[1])
    datos = obtener_cumple_por_id(id_cumple)
    
    if not datos:
        return await query.edit_message_text("❌ Error: Perfil no encontrado.")
        
    id_bd, chat_id, nombre, fecha, anio, categoria, telefono = datos
    
    perfil = f"👤 *Perfil de {nombre}*\n\n"
    perfil += f"📅 Fecha: {fecha}\n"
    perfil += f"🗓️ Año: {anio}\n"
    perfil += f"🏷️ Categoría: {categoria}\n"
    perfil += f"📱 Teléfono: {telefono if telefono else 'No guardado'}"
    
    teclado = [
        [InlineKeyboardButton("🗑️ Borrar", callback_data=f"borrar_{id_bd}")],
        [InlineKeyboardButton("🔙 Volver a la lista", callback_data="list_todos")]
    ]
    await query.edit_message_text(text=perfil, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(teclado))

async def borrar_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    id_cumple = int(query.data.split('_')[1])
    borrar_cumple_por_id(id_cumple)
    
    teclado = [[InlineKeyboardButton("🔙 Volver a la lista", callback_data="list_todos")]]
    await query.edit_message_text("🗑️ Cumpleaños eliminado correctamente.", reply_markup=InlineKeyboardMarkup(teclado))


# --- AJUSTES Y EXPORTAR ---
async def ajustes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hora_actual = obtener_preferencia(update.message.chat_id)
    teclado = [
        [InlineKeyboardButton("09:00", callback_data="hora_09:00"), InlineKeyboardButton("10:00", callback_data="hora_10:00")],
        [InlineKeyboardButton("12:00", callback_data="hora_12:00"), InlineKeyboardButton("18:00", callback_data="hora_18:00")]
    ]
    mensaje = f"⚙️ *Ajustes de Alarma*\n\nActualmente el bot te avisa a las: *{hora_actual}*\n\n¿A qué hora prefieres que te avise?"
    await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(teclado), parse_mode="Markdown")

async def guardar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nueva_hora = query.data.split('_')[1]
    guardar_preferencia(query.message.chat_id, nueva_hora)
    await query.edit_message_text(f"✅ ¡Hecho! Te avisaré de los cumpleaños a las {nueva_hora} (Hora de España).")

async def exportar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    cumples = obtener_cumples_por_usuario(chat_id)
    
    if not cumples:
        return await update.message.reply_text("No tienes cumpleaños guardados para exportar.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nombre', 'Fecha', 'Año', 'Categoría', 'Teléfono'])
    
    for c in cumples:
        writer.writerow([c[1], c[2], c[3], c[4], c[5]])

    output.seek(0)
    await context.bot.send_document(
        chat_id=chat_id,
        document=output.getvalue().encode('utf-8'),
        filename="mis_cumpleaños.csv",
        caption="📊 Aquí tienes la copia de seguridad de todos tus cumpleaños para abrir en Excel."
    )


# --- ALARMA DE PRODUCCIÓN (TICK POR MINUTO) ---
def generar_mensaje_y_teclado(id_cumple, nombre, anio, categoria, telefono, texto_anterior=""):
    año_actual = datetime.now().year
    mensaje = f"🔔 *¡RECORDATORIO AUTOMÁTICO!*\n\n"
    if anio != "Desconocido" and str(anio).isdigit(): 
        mensaje += f"Hoy es el cumpleaños de {nombre} ({año_actual - int(anio)} años) 🎂\n"
    else: 
        mensaje += f"Hoy es el cumpleaños de {nombre} 🎂\n"
    
    teclado_alarma = []
    if categoria in SUGERENCIAS:
        opciones = SUGERENCIAS[categoria]
        if len(opciones) > 1 and texto_anterior:
            opciones_validas = [opt for opt in opciones if opt not in texto_anterior]
            idea = random.choice(opciones_validas) if opciones_validas else random.choice(opciones)
        else:
            idea = random.choice(opciones)
            
        mensaje += f"\n💡 *Sugerencia:*\n{idea}\n"
        texto_codificado = urllib.parse.quote_plus(idea)
        
        teclado_alarma.append([
            InlineKeyboardButton("📋 Copiar mensaje", copy_text=CopyTextButton(text=idea)),
            InlineKeyboardButton("🔄 Generar otro", callback_data=f"otra_{id_cumple}")
        ])
        
        botones_envio = []
        if telefono and telefono != "":
            botones_envio.append(InlineKeyboardButton("🟢 WhatsApp", url=f"https://api.whatsapp.com/send?phone={telefono}&text={texto_codificado}"))
            botones_envio.append(InlineKeyboardButton("🔵 Telegram", url=f"https://t.me/+{telefono}?text={texto_codificado}"))
        else:
            botones_envio.append(InlineKeyboardButton("🟢 WhatsApp", url=f"https://api.whatsapp.com/send?text={texto_codificado}"))
            botones_envio.append(InlineKeyboardButton("🔵 Compartir TG", url=f"https://t.me/share/url?url={texto_codificado}"))
            
        teclado_alarma.append(botones_envio)
        
    return mensaje, InlineKeyboardMarkup(teclado_alarma) if teclado_alarma else None

async def cambiar_sugerencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    id_cumple = int(query.data.split('_')[1])
    datos = obtener_cumple_por_id(id_cumple)
    if datos:
        id_bd, chat_id, nombre, fecha, anio, categoria, telefono = datos
        texto_anterior = query.message.text or ""
        mensaje, teclado = generar_mensaje_y_teclado(id_bd, nombre, anio, categoria, telefono, texto_anterior)
        try:
            await query.edit_message_text(text=mensaje, reply_markup=teclado, parse_mode="Markdown")
            await query.answer() 
        except BadRequest:
            await query.answer()

async def tick_alarmas(context: ContextTypes.DEFAULT_TYPE):
    # Forzamos la zona horaria a España para evitar errores en servidores extranjeros
    zona_horaria = pytz.timezone('Europe/Madrid')
    ahora = datetime.now(zona_horaria)
    hora_actual = ahora.strftime("%H:%M")
    dia_mes_actual = ahora.strftime("%d/%m")

    cumples_hoy = obtener_cumples_hoy(dia_mes_actual)
    if not cumples_hoy: return

    # Agrupamos por usuario
    usuarios_hoy = {}
    for c in cumples_hoy:
        chat_id = c[1]
        if chat_id not in usuarios_hoy:
            usuarios_hoy[chat_id] = []
        usuarios_hoy[chat_id].append(c)

    # Revisamos si es la hora preferida de cada usuario
    for chat_id, lista_cumples in usuarios_hoy.items():
        pref_hora = obtener_preferencia(chat_id)
        if pref_hora == hora_actual:
            for c in lista_cumples:
                id_bd, _, nombre, fecha, anio, categoria, telefono = c
                mensaje, teclado = generar_mensaje_y_teclado(id_bd, nombre, anio, categoria, telefono)
                await context.bot.send_message(chat_id=chat_id, text=mensaje, parse_mode="Markdown", reply_markup=teclado)


if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("exportar", exportar_cmd))
    app.add_handler(CommandHandler("ajustes", ajustes_cmd))
    app.add_handler(CallbackQueryHandler(guardar_hora, pattern="^hora_"))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevo', nuevo_inicio), CallbackQueryHandler(nuevo_inicio, pattern="^start_nuevo$")],
        states={
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_nombre)],
            MES: [CallbackQueryHandler(recibir_mes, pattern="^mes_")],
            DIA: [CallbackQueryHandler(recibir_dia, pattern="^dia_")],
            PREGUNTA_ANIO: [CallbackQueryHandler(preguntar_anio_callback, pattern="^(si_anio|no_anio)$")],
            SELECCIONAR_ANIO: [CallbackQueryHandler(navegar_anios, pattern="^nav_anio_"), CallbackQueryHandler(recibir_anio_btn, pattern="^anio_")],
            CATEGORIA: [CallbackQueryHandler(recibir_categoria, pattern="^(Familia|Amigos|Trabajo|Ninguna)$")],
            PREGUNTA_TELEFONO: [CallbackQueryHandler(preguntar_telefono_callback, pattern="^(si_tel|no_tel)$")],
            RECIBIR_TELEFONO: [
                CallbackQueryHandler(manejar_teclado_telefono, pattern="^num_"),
                MessageHandler(filters.CONTACT, recibir_contacto),
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono_texto)
            ]
        },
        fallbacks=[CommandHandler('cancelar', cancelar)],
    )
    
    app.add_handler(conv_handler)
    
    # Manejadores del Listado
    app.add_handler(CommandHandler("listar", listar_inicio))
    app.add_handler(CallbackQueryHandler(listar_inicio, pattern="^start_listar$"))
    app.add_handler(CallbackQueryHandler(volver_listar, pattern="^list_volver$"))
    app.add_handler(CallbackQueryHandler(manejar_listar, pattern="^list_(proximos|mes|todos)$"))
    app.add_handler(CallbackQueryHandler(ver_perfil_cumple, pattern="^ver_"))
    app.add_handler(CallbackQueryHandler(borrar_inline, pattern="^borrar_"))
    
    app.add_handler(CallbackQueryHandler(cambiar_sugerencia, pattern="^otra_"))
    
    print("Bot Cumpleping iniciado y funcionando en modo Producción...")
    # El bot comprobará la base de datos cada 60 segundos
    app.job_queue.run_repeating(tick_alarmas, interval=60, first=5)
    app.run_polling()
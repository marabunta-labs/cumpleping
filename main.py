import os
import urllib.parse
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from datetime import datetime
import random
from database import agregar_cumple, obtener_cumples_hoy, obtener_cumple_por_id, borrar_cumple
from mensajes import SUGERENCIAS

NOMBRE, MES, DIA, PREGUNTA_ANIO, SELECCIONAR_ANIO, CATEGORIA, PREGUNTA_TELEFONO, RECIBIR_TELEFONO = range(8)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- BÁSICOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [[InlineKeyboardButton("➕ Añadir Cumpleaños", callback_data="start_nuevo")]]
    await update.message.reply_text(
        "¡Hola! Soy Cumpleping 🎂.\nTe ayudaré a recordar todos los cumpleaños y te sugeriré cómo felicitarlos.",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Pong! 🏓 Estoy vivo.")

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
    await update.message.reply_text(f"Perfecto, guardaré a {context.user_data['nombre']}.\n\n¿En qué mes nació?", reply_markup=InlineKeyboardMarkup(teclado))
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
    botones = []
    fila = []
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
    texto = "¡Año guardado! ¿En qué categoría lo guardamos?"
    try: await mensaje_o_query.edit_message_text(text=texto, reply_markup=InlineKeyboardMarkup(teclado))
    except: await mensaje_o_query.reply_text(text=texto, reply_markup=InlineKeyboardMarkup(teclado))
    return CATEGORIA

async def recibir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['categoria'] = query.data
    teclado = [[InlineKeyboardButton("Sí, añadir número", callback_data="si_tel")], [InlineKeyboardButton("No, terminar", callback_data="no_tel")]]
    await query.edit_message_text("Última pregunta: ¿Quieres añadir su teléfono para enviarle el WhatsApp directo con 1 clic?", reply_markup=InlineKeyboardMarkup(teclado))
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
        texto = f"Usa el teclado, escríbelo, o **comparte un contacto** desde tu agenda 📎:\n\n📱 Número: `{context.user_data['telefono_temp']}`"
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
        
    texto = f"Usa el teclado, escríbelo, o **comparte un contacto** desde tu agenda 📎:\n\n📱 Número: `{context.user_data['telefono_temp']}`"
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
    
    resumen = f"✅ ¡Guardado con éxito!\n\n👤 {context.user_data['nombre']}\n📅 {context.user_data['fecha']}\n🗓️ Año: {context.user_data['anio']}\n🏷️ Categoría: {context.user_data['categoria']}"
    if context.user_data['telefono']: resumen += f"\n📱 Teléfono: +{context.user_data['telefono']}"
    try: await mensaje_o_query.edit_message_text(text=resumen)
    except: await mensaje_o_query.reply_text(text=resumen)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Creación cancelada.")
    return ConversationHandler.END

# --- COMANDOS Y ALARMA ---
async def borrar_cumple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("⚠️ Uso: /borrar [Nombre]")
    nombre = " ".join(context.args)
    if borrar_cumple(update.message.chat_id, nombre): await update.message.reply_text(f"🗑️ Eliminado {nombre}.")
    else: await update.message.reply_text(f"❌ No encontré a '{nombre}'.")

async def cumples_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cumpleañeros = obtener_cumples_hoy(datetime.now().strftime("%d/%m"))
    if not cumpleañeros: return await update.message.reply_text("Hoy no hay cumpleaños. ¡Día libre! 🏖️")
    mensaje = "🎉 **¡Cumpleaños de hoy!** 🎉\n\n"
    for id_bd, chat_id, nombre, fecha, anio, categoria, telefono in cumpleañeros:
        if anio != "Desconocido" and str(anio).isdigit(): mensaje += f"🎂 {nombre} cumple {datetime.now().year - int(anio)} años\n"
        else: mensaje += f"🎂 {nombre} cumple años hoy\n"
    await update.message.reply_text(mensaje, parse_mode="Markdown")
    
def generar_mensaje_y_teclado(id_cumple, nombre, anio, categoria, telefono):
    año_actual = datetime.now().year
    mensaje = f"🔔 *¡RECORDATORIO AUTOMÁTICO!*\n\n"
    if anio != "Desconocido" and str(anio).isdigit(): 
        mensaje += f"Hoy es el cumpleaños de {nombre} ({año_actual - int(anio)} años) 🎂\n"
    else: 
        mensaje += f"Hoy es el cumpleaños de {nombre} 🎂\n"
    mensaje += f"Categoría: {categoria}\n\n"
    
    teclado_alarma = []
    if categoria in SUGERENCIAS:
        idea = random.choice(SUGERENCIAS[categoria])
        # Ya no usamos las comillas invertidas (```) porque tenemos botón
        mensaje += f"💡 *Sugerencia:*\n{idea}\n"
        
        texto_codificado = urllib.parse.quote(idea)
        
        # Fila 1: Botón de COPIAR y Botón de CAMBIAR
        teclado_alarma.append([
            InlineKeyboardButton("📋 Copiar", copy_text=CopyTextButton(text=idea)),
            InlineKeyboardButton("🔄 Otra opción", callback_data=f"otra_{id_cumple}")
        ])
        
        # Fila 2: Botones de envío
        botones_envio = []
        if telefono and telefono != "":
            # Si hay teléfono, WA pre-rellena, TG abre el chat directo (para que pegues)
            link_wa = f"[https://wa.me/](https://wa.me/){telefono}?text={texto_codificado}"
            link_tg = f"[https://t.me/](https://t.me/)+{telefono}"
            botones_envio.append(InlineKeyboardButton("🟢 WhatsApp", url=link_wa))
            botones_envio.append(InlineKeyboardButton("🔵 Telegram", url=link_tg))
        else:
            # Si no hay teléfono, ambos abren el menú genérico de compartir
            link_wa = f"[https://wa.me/?text=](https://wa.me/?text=){texto_codificado}"
            link_tg = f"[https://t.me/share/url?url=](https://t.me/share/url?url=){texto_codificado}"
            botones_envio.append(InlineKeyboardButton("🟢 WhatsApp", url=link_wa))
            botones_envio.append(InlineKeyboardButton("🔵 Compartir TG", url=link_tg))
            
        teclado_alarma.append(botones_envio)
        
    return mensaje, InlineKeyboardMarkup(teclado_alarma) if teclado_alarma else None

async def cambiar_sugerencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    id_cumple = int(query.data.split('_')[1])
    datos = obtener_cumple_por_id(id_cumple)
    if datos:
        id_bd, chat_id, nombre, fecha, anio, categoria, telefono = datos
        mensaje, teclado = generar_mensaje_y_teclado(id_bd, nombre, anio, categoria, telefono)
        await query.edit_message_text(text=mensaje, reply_markup=teclado, parse_mode="Markdown")

async def alarma_diaria(context: ContextTypes.DEFAULT_TYPE):
    cumpleañeros = obtener_cumples_hoy(datetime.now().strftime("%d/%m"))
    for id_bd, chat_id, nombre, fecha, anio, categoria, telefono in cumpleañeros:
        mensaje, teclado = generar_mensaje_y_teclado(id_bd, nombre, anio, categoria, telefono)
        await context.bot.send_message(chat_id=chat_id, text=mensaje, parse_mode="Markdown", reply_markup=teclado)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    
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
    app.add_handler(CommandHandler("borrar", borrar_cumple_cmd))
    app.add_handler(CommandHandler("hoy", cumples_hoy))
    
    # Manejador para el botón de "Otra opción"
    app.add_handler(CallbackQueryHandler(cambiar_sugerencia, pattern="^otra_"))
    
    print("Bot Cumpleping iniciado...")
    app.job_queue.run_repeating(alarma_diaria, interval=10, first=5)
    app.run_polling()
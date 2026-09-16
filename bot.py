"""
Bot de Telegram "Ayudante Escolar" para un curso de estudiantes.
Funciones: preguntas de estudio, resúmenes, generación de Word/PowerPoint/
páginas web, horarios, exámenes compartidos y agenda privada por alumno.
"""
import os
import json
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import db
import ai
import files

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "cambiaesto")


# ---------------------------------------------------------------------------
# Comandos básicos
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.first_name, user.username)
    await update.message.reply_text(
        f"¡Hola {user.first_name}! 👋 Soy el Ayudante Escolar del curso.\n\n"
        "Puedo ayudarte con:\n"
        "📚 Preguntas de teoría o dudas de materias (escribime directo)\n"
        "📝 /resumen <texto o pegale a una foto> - resumir apuntes\n"
        "📄 /word <tema> - crear un Word sobre un tema\n"
        "📊 /ppt <tema> - crear un PowerPoint sobre un tema\n"
        "🌐 /web <tema> - crear una página web simple sobre un tema\n"
        "📅 /horario [día] - ver el horario de clases\n"
        "🗓️ /examenes - ver fechas de examen/entregas cargadas\n"
        "➕ /cargar_examen <materia> | <fecha> | <descripción>\n"
        "🙋 /agenda - ver tu agenda personal (privada, solo vos la ves)\n"
        "➕ /agendar <fecha> | <qué> - agregar algo a tu agenda\n"
        "📤 Mandame una FOTO de tu carpeta y la guardo como apunte para todo el curso\n\n"
        "Solo respondo cosas relacionadas a la escuela y el estudio 🎓"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def hacerme_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin <contraseña> - para que el profe/organizador pueda cargar horarios."""
    if not context.args:
        await update.message.reply_text("Uso: /admin <contraseña>")
        return
    if context.args[0] == ADMIN_PASSWORD:
        db.make_admin(update.effective_user.id)
        await update.message.reply_text("Listo, ahora sos admin ✅ (podés cargar horarios).")
    else:
        await update.message.reply_text("Contraseña incorrecta.")


# ---------------------------------------------------------------------------
# Preguntas libres (IA) -> usa apuntes compartidos como contexto si aplica
# ---------------------------------------------------------------------------
async def responder_pregunta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.first_name, user.username)
    pregunta = update.message.text

    # Busca contexto relevante en el conocimiento compartido (apuntes, tareas ya resueltas)
    palabras_clave = [p for p in pregunta.split() if len(p) > 4][:3]
    contexto = ""
    for palabra in palabras_clave:
        resultados = db.search_shared_knowledge(palabra, limit=2)
        for r in resultados:
            contexto += f"\n[Apunte de {r['materia'] or 'general'} - {r['tema'] or ''}]: {r['contenido'][:500]}"

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    respuesta = ai.ask_ai(pregunta, contexto_extra=contexto)
    await update.message.reply_text(respuesta)


# ---------------------------------------------------------------------------
# Fotos de la carpeta -> se guardan como conocimiento compartido
# ---------------------------------------------------------------------------
async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.first_name, user.username)

    foto = update.message.photo[-1]
    tg_file = await foto.get_file()
    image_bytes = bytes(await tg_file.download_as_bytearray())

    caption = update.message.caption or ""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if caption:
        # Si mandó la foto con una pregunta puntual, responde directo
        respuesta = ai.ask_ai_with_image(caption, image_bytes)
        await update.message.reply_text(respuesta)
    else:
        # Si no, la guarda como apunte compartido para todo el curso
        texto_extraido = ai.extract_text_from_image(image_bytes)
        db.add_shared_knowledge(
            materia="sin especificar",
            tema="foto de apuntes",
            contenido=texto_extraido,
            subido_por=user.id,
        )
        await update.message.reply_text(
            "📸 ¡Guardado! Agregué esta foto como apunte compartido para todo el curso.\n\n"
            f"Resumen de lo que reconocí:\n{texto_extraido[:800]}"
        )


# ---------------------------------------------------------------------------
# Resumen de texto
# ---------------------------------------------------------------------------
async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    if not texto and update.message.reply_to_message:
        texto = update.message.reply_to_message.text or ""
    if not texto:
        await update.message.reply_text(
            "Mandame el texto así: /resumen <texto>, o respondé a un mensaje con /resumen."
        )
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    respuesta = ai.ask_ai(f"Resumime esto de forma clara y ordenada:\n\n{texto}")
    await update.message.reply_text(respuesta)


# ---------------------------------------------------------------------------
# Generar Word
# ---------------------------------------------------------------------------
async def crear_word_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Uso: /word <tema>  (ej: /word La Revolución de Mayo)")
        return
    await update.message.reply_text("Armando el Word, un toque... 📄")
    contenido = ai.ask_ai(
        f"Escribí el contenido de un documento Word educativo sobre '{tema}'. "
        "Usá '# ' antes de cada título de sección, y líneas normales para párrafos. "
        "Estructura sugerida: introducción, 3-4 secciones con desarrollo, y una conclusión. "
        "No uses markdown como asteriscos, solo texto plano y '# ' para títulos."
    )
    path = files.crear_word(tema, contenido)
    await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))


# ---------------------------------------------------------------------------
# Generar PowerPoint
# ---------------------------------------------------------------------------
async def crear_ppt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Uso: /ppt <tema>  (ej: /ppt Fotosíntesis)")
        return
    await update.message.reply_text("Armando el PowerPoint, un toque... 📊")

    prompt = (
        f"Generá el esquema de una presentación educativa sobre '{tema}' en formato JSON. "
        'Devolvé SOLO un JSON válido con esta forma exacta, sin texto extra ni markdown:\n'
        '{"diapositivas": [{"titulo": "...", "puntos": ["...", "..."]}]}\n'
        "Entre 5 y 7 diapositivas, cada una con 3-5 puntos cortos (no párrafos largos)."
    )
    respuesta = ai.ask_ai(prompt)
    respuesta_limpia = respuesta.strip().strip("`").replace("json\n", "", 1)
    try:
        data = json.loads(respuesta_limpia)
        diapositivas = data["diapositivas"]
    except Exception:
        logger.warning("No se pudo parsear JSON del ppt, usando fallback simple.")
        diapositivas = [{"titulo": tema, "puntos": [respuesta[:300]]}]

    path = files.crear_powerpoint(tema, diapositivas)
    await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))


# ---------------------------------------------------------------------------
# Generar página web simple
# ---------------------------------------------------------------------------
async def crear_web_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Uso: /web <tema>  (ej: /web Sistema Solar)")
        return
    await update.message.reply_text("Armando la página web, un toque... 🌐")
    html_body = ai.ask_ai(
        f"Generá el contenido HTML (solo lo que va dentro de <body>, con <h1>, <h2>, "
        f"<p>, <ul><li>) de una página web educativa simple sobre '{tema}'. "
        "No incluyas <html>, <head> ni <style>, solo el contenido del body. Sin markdown."
    )
    path = files.crear_pagina_web(tema, html_body)
    await update.message.reply_document(document=open(path, "rb"), filename=os.path.basename(path))
    await update.message.reply_text(
        "Te mandé el archivo .html. Lo podés abrir en el navegador, o subir el texto "
        "a Lovable/Canva si querés algo más visual."
    )


# ---------------------------------------------------------------------------
# Horarios (compartido)
# ---------------------------------------------------------------------------
async def horario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dia = " ".join(context.args) if context.args else None
    filas = db.get_horario(dia)
    if not filas:
        await update.message.reply_text(
            "Todavía no hay horarios cargados. Un admin puede cargarlos con "
            "/cargar_horario <día> | <hora> | <materia>"
        )
        return
    texto = "📅 Horario:\n"
    for f in filas:
        texto += f"- {f['dia']} {f['hora']}: {f['materia']}\n"
    await update.message.reply_text(texto)


async def cargar_horario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(
            "Solo un admin puede cargar horarios. Pedile a tu profe/organizador que use /admin."
        )
        return
    texto = " ".join(context.args)
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) != 3:
        await update.message.reply_text("Uso: /cargar_horario <día> | <hora> | <materia>")
        return
    dia, hora, materia = partes
    db.add_horario(dia, hora, materia)
    await update.message.reply_text(f"✅ Cargado: {dia} {hora} - {materia}")


# ---------------------------------------------------------------------------
# Exámenes / entregas (compartido, cualquiera puede cargar)
# ---------------------------------------------------------------------------
async def examenes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filas = db.get_examenes()
    if not filas:
        await update.message.reply_text(
            "No hay exámenes/entregas cargados todavía. Cargá uno con "
            "/cargar_examen <materia> | <fecha> | <descripción>"
        )
        return
    texto = "🗓️ Exámenes y entregas:\n"
    for f in filas:
        texto += f"- {f['fecha']} | {f['materia']}: {f['descripcion']}\n"
    await update.message.reply_text(texto)


async def cargar_examen_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) != 3:
        await update.message.reply_text(
            "Uso: /cargar_examen <materia> | <fecha> | <descripción>"
        )
        return
    materia, fecha, descripcion = partes
    db.add_examen(materia, fecha, descripcion, update.effective_user.id)
    await update.message.reply_text(f"✅ Cargado para todo el curso: {materia} - {fecha}")


# ---------------------------------------------------------------------------
# Agenda privada (nunca se comparte)
# ---------------------------------------------------------------------------
async def agenda_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filas = db.get_agenda(update.effective_user.id)
    if not filas:
        await update.message.reply_text(
            "Tu agenda está vacía. Agregá algo con /agendar <fecha> | <qué>"
        )
        return
    texto = "🙋 Tu agenda personal (solo vos la ves):\n"
    for f in filas:
        texto += f"- {f['fecha']}: {f['descripcion']}\n"
    await update.message.reply_text(texto)


async def agendar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    partes = [p.strip() for p in texto.split("|")]
    if len(partes) != 2:
        await update.message.reply_text("Uso: /agendar <fecha> | <qué tenés que hacer>")
        return
    fecha, descripcion = partes
    db.add_agenda_item(update.effective_user.id, descripcion, fecha)
    await update.message.reply_text(f"✅ Agregado a tu agenda: {fecha} - {descripcion}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    db.init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", hacerme_admin))
    app.add_handler(CommandHandler("resumen", resumen))
    app.add_handler(CommandHandler("word", crear_word_cmd))
    app.add_handler(CommandHandler("ppt", crear_ppt_cmd))
    app.add_handler(CommandHandler("web", crear_web_cmd))
    app.add_handler(CommandHandler("horario", horario_cmd))
    app.add_handler(CommandHandler("cargar_horario", cargar_horario_cmd))
    app.add_handler(CommandHandler("examenes", examenes_cmd))
    app.add_handler(CommandHandler("cargar_examen", cargar_examen_cmd))
    app.add_handler(CommandHandler("agenda", agenda_cmd))
    app.add_handler(CommandHandler("agendar", agendar_cmd))

    app.add_handler(MessageHandler(filters.PHOTO, recibir_foto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_pregunta))

    logger.info("Bot arrancando...")
    app.run_polling()


if __name__ == "__main__":
    main()

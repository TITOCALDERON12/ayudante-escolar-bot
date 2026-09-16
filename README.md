# Ayudante Escolar - Bot de Telegram

Este bot ayuda a un curso de estudiantes con temas escolares: preguntas de teoría,
resúmenes, generación de Word/PowerPoint/páginas web, horarios, exámenes
compartidos y agenda personal privada.

Las instrucciones completas para subir esto a internet gratis están en el chat
de Claude donde se armó este proyecto. En resumen:

1. Subir estos archivos a un repositorio de GitHub (gratis)
2. Crear una cuenta en Render.com (gratis) y conectarla a ese repositorio
3. Cargar las variables de entorno: TELEGRAM_TOKEN, GEMINI_API_KEY, ADMIN_PASSWORD
4. Comando de arranque: `python bot.py`

## Variables de entorno necesarias
- `TELEGRAM_TOKEN`: el token que te dio @BotFather en Telegram
- `GEMINI_API_KEY`: la API key de Google AI Studio (empieza con AQ. o AIzaSy)
- `ADMIN_PASSWORD`: una contraseña que elijas vos, para que quien la sepa pueda
  cargar los horarios del curso con /admin <contraseña>

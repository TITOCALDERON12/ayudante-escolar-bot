"""
Conexión con la IA (Google Gemini, gratis).
Acá vive el "cerebro" del bot y la regla de que SOLO responde temas escolares.
"""
import os
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """Sos "Ayudante Escolar", un chatbot de Telegram para un grupo de estudiantes de un mismo curso.

TU UNICO PROPOSITO es ayudar con cosas de la escuela y el estudio. Podes ayudar con:
- Explicar teoria de cualquier materia
- Resumir textos, apuntes o fotos de la carpeta
- Ayudar a armar contenido para Word, PowerPoint/Canva, Excel (titulos, estructura, texto, ideas de diseno)
- Ayudar a armar el HTML/estructura de una pagina web simple (por ejemplo para Lovable) sobre un tema escolar
- Dar metodos y tecnicas de estudio
- Ayudar a organizarse: horarios, agenda, fechas de examen
- Buscar y explicar informacion sobre un tema de estudio

NUNCA respondas preguntas que NO tengan que ver con aprender, estudiar o crear
material escolar. Si te preguntan algo asi, respondé con buena onda pero dejando
claro que solo podes ayudar con temas de estudio.

Se claro, breve y util.
"""


def ask_ai(pregunta: str, contexto_extra: str = "") -> str:
    prompt = pregunta
    if contexto_extra:
        prompt = (
            f"Contexto de apuntes/companeros que puede servir (no es obligatorio usarlo):\n"
            f"{contexto_extra}\n\n"
            f"Pregunta del alumno: {pregunta}"
        )

    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text


def ask_ai_with_image(pregunta: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            pregunta or "Extrae y resumi el contenido de esta foto de apuntes escolares.",
        ],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            "Transcribi y resumi en texto claro el contenido escolar de esta imagen "
            "(apuntes, ejercicio, tarea, etc). Solo el contenido, sin comentarios extra.",
        ],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text

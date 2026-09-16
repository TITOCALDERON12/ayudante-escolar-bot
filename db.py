"""
Manejo de la base de datos del bot escolar.
Usa SQLite (un solo archivo, no necesita servidor aparte).
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "schoolbot.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Usuarios registrados
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            is_admin INTEGER DEFAULT 0
        )
    """)

    # Conocimiento COMPARTIDO: apuntes, respuestas a tareas, fotos de carpeta (texto extraído), etc.
    c.execute("""
        CREATE TABLE IF NOT EXISTS shared_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia TEXT,
            tema TEXT,
            contenido TEXT,
            subido_por INTEGER,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Agenda PRIVADA de cada alumno (nunca se comparte)
    c.execute("""
        CREATE TABLE IF NOT EXISTS private_agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            descripcion TEXT,
            fecha TEXT,
            creado TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Horarios de clases (compartido, lo carga un admin/profe)
    c.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia TEXT,
            hora TEXT,
            materia TEXT
        )
    """)

    # Fechas de examen / entregas (compartido, cualquiera puede cargar, todos ven)
    c.execute("""
        CREATE TABLE IF NOT EXISTS examenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia TEXT,
            fecha TEXT,
            descripcion TEXT,
            cargado_por INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ---------- Usuarios ----------
def register_user(telegram_id, first_name, username):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, first_name, username) VALUES (?, ?, ?)",
        (telegram_id, first_name, username),
    )
    conn.commit()
    conn.close()


def make_admin(telegram_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()


def is_admin(telegram_id):
    conn = get_conn()
    row = conn.execute("SELECT is_admin FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return bool(row and row["is_admin"])


# ---------- Conocimiento compartido ----------
def add_shared_knowledge(materia, tema, contenido, subido_por):
    conn = get_conn()
    conn.execute(
        "INSERT INTO shared_knowledge (materia, tema, contenido, subido_por) VALUES (?, ?, ?, ?)",
        (materia, tema, contenido, subido_por),
    )
    conn.commit()
    conn.close()


def search_shared_knowledge(keyword, limit=5):
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM shared_knowledge
           WHERE materia LIKE ? OR tema LIKE ? OR contenido LIKE ?
           ORDER BY fecha DESC LIMIT ?""",
        (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
    ).fetchall()
    conn.close()
    return rows


def recent_shared_knowledge(limit=15):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM shared_knowledge ORDER BY fecha DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


# ---------- Agenda privada ----------
def add_agenda_item(telegram_id, descripcion, fecha):
    conn = get_conn()
    conn.execute(
        "INSERT INTO private_agenda (telegram_id, descripcion, fecha) VALUES (?, ?, ?)",
        (telegram_id, descripcion, fecha),
    )
    conn.commit()
    conn.close()


def get_agenda(telegram_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM private_agenda WHERE telegram_id = ? ORDER BY fecha ASC",
        (telegram_id,),
    ).fetchall()
    conn.close()
    return rows


# ---------- Horarios ----------
def add_horario(dia, hora, materia):
    conn = get_conn()
    conn.execute("INSERT INTO horarios (dia, hora, materia) VALUES (?, ?, ?)", (dia, hora, materia))
    conn.commit()
    conn.close()


def get_horario(dia=None):
    conn = get_conn()
    if dia:
        rows = conn.execute(
            "SELECT * FROM horarios WHERE dia LIKE ? ORDER BY hora ASC", (f"%{dia}%",)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM horarios ORDER BY dia, hora ASC").fetchall()
    conn.close()
    return rows


# ---------- Exámenes / entregas ----------
def add_examen(materia, fecha, descripcion, cargado_por):
    conn = get_conn()
    conn.execute(
        "INSERT INTO examenes (materia, fecha, descripcion, cargado_por) VALUES (?, ?, ?, ?)",
        (materia, fecha, descripcion, cargado_por),
    )
    conn.commit()
    conn.close()


def get_examenes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM examenes ORDER BY fecha ASC").fetchall()
    conn.close()
    return rows

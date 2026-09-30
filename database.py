import sqlite3

def crear_base_datos():
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    # Tabla de cumpleaños
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cumpleaños (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            nombre TEXT,
            fecha TEXT,
            anio TEXT,
            categoria TEXT,
            telefono TEXT
        )
    ''')
    # NUEVA: Tabla de ajustes de usuario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferencias (
            chat_id INTEGER PRIMARY KEY,
            hora_alarma TEXT
        )
    ''')
    conexion.commit()
    conexion.close()
    print("Base de datos lista.")

def agregar_cumple(chat_id, nombre, fecha, anio, categoria, telefono):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO cumpleaños (chat_id, nombre, fecha, anio, categoria, telefono)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (chat_id, nombre, fecha, anio, categoria, telefono))
    conexion.commit()
    conexion.close()  

def obtener_cumples_hoy(dia_mes):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT id, chat_id, nombre, fecha, anio, categoria, telefono FROM cumpleaños 
        WHERE fecha LIKE ?
    ''', (f"{dia_mes}%",))
    resultados = cursor.fetchall()
    conexion.close()
    return resultados

def obtener_cumple_por_id(id_cumple):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT id, chat_id, nombre, fecha, anio, categoria, telefono FROM cumpleaños 
        WHERE id = ?
    ''', (id_cumple,))
    resultado = cursor.fetchone()
    conexion.close()
    return resultado

def obtener_cumples_por_usuario(chat_id):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT id, nombre, fecha, anio, categoria, telefono 
        FROM cumpleaños 
        WHERE chat_id = ?
    ''', (chat_id,))
    resultados = cursor.fetchall()
    conexion.close()
    return resultados

def borrar_cumple(chat_id, nombre):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT count(*) FROM cumpleaños 
        WHERE chat_id = ? AND nombre = ?
    ''', (chat_id, nombre))
    existe = cursor.fetchone()[0] > 0
    if existe:
        cursor.execute('''
            DELETE FROM cumpleaños 
            WHERE chat_id = ? AND nombre = ?
        ''', (chat_id, nombre))
        conexion.commit()
    conexion.close()
    return existe

def borrar_cumple_por_id(id_cumple):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('DELETE FROM cumpleaños WHERE id = ?', (id_cumple,))
    conexion.commit()
    conexion.close()

def obtener_preferencia(chat_id):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('SELECT hora_alarma FROM preferencias WHERE chat_id = ?', (chat_id,))
    resultado = cursor.fetchone()
    conexion.close()
    return resultado[0] if resultado else "09:00" # Por defecto a las 9 AM

def guardar_preferencia(chat_id, hora_alarma):
    conexion = sqlite3.connect('cumpleping.db')
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO preferencias (chat_id, hora_alarma) 
        VALUES (?, ?) 
        ON CONFLICT(chat_id) DO UPDATE SET hora_alarma=excluded.hora_alarma
    ''', (chat_id, hora_alarma))
    conexion.commit()
    conexion.close()

if __name__ == '__main__':
    crear_base_datos()
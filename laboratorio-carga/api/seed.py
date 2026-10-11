r"""Crea (o reinicia) la base SQLite con 20 productos ficticios.

Ejecutar en Windows (desde laboratorio-carga) antes de cada prueba, para
partir siempre del mismo estado:
    python api\seed.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).with_name("tienda.db")

# Datos ficticios: nombre y precio en pesos (no corresponden a nada real)
PRODUCTOS = [
    ("Cuaderno universitario", 8500), ("Bolígrafo azul", 1500),
    ("Lápiz HB", 900), ("Borrador", 700), ("Regla 30 cm", 2500),
    ("Calculadora científica", 65000), ("Mochila", 95000),
    ("Resaltador amarillo", 2800), ("Carpeta plástica", 3200),
    ("Memoria USB 32 GB", 28000), ("Audífonos", 45000),
    ("Mouse inalámbrico", 39000), ("Teclado", 72000),
    ("Termo 500 ml", 30000), ("Agenda 2026", 22000),
    ("Marcador permanente", 3500), ("Cinta adhesiva", 2000),
    ("Tijeras", 4500), ("Pegante en barra", 3000), ("Post-it", 5000),
]


def sembrar():
    with sqlite3.connect(DB) as con:
        # WAL: permite leer mientras otro hilo escribe (evita bloqueos de la BD)
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript("""
            DROP TABLE IF EXISTS pedidos;
            DROP TABLE IF EXISTS productos;
            CREATE TABLE productos (
                id     INTEGER PRIMARY KEY,
                nombre TEXT    NOT NULL,
                precio INTEGER NOT NULL
            );
            CREATE TABLE pedidos (
                id          INTEGER PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                cantidad    INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 10),
                creado      TEXT    DEFAULT CURRENT_TIMESTAMP
            );
        """)
        con.executemany(
            "INSERT INTO productos (nombre, precio) VALUES (?, ?)", PRODUCTOS
        )
    print(f"Base creada en {DB} con {len(PRODUCTOS)} productos y 0 pedidos.")


if __name__ == "__main__":
    sembrar()

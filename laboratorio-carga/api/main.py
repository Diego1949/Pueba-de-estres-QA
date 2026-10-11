"""API de la tienda ficticia que vamos a someter a carga.

Iniciar en Windows (desde la carpeta laboratorio-carga, con el entorno activado):
    uvicorn api.main:app --workers 1 --port 8000 --no-access-log

Todos los endpoints son síncronos (def): FastAPI los ejecuta en un pool de
hilos y, como Python tiene GIL, solo un hilo calcula a la vez. Con 1 solo
worker, el endpoint pesado /api/reporte termina frenando a todos los demás.
"""
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB = Path(__file__).with_name("tienda.db")

# Cuánto "trabaja" el reporte. Calibrado para que F1 y F2 sean estables y la
# degradación aparezca entre F3 y F5 (ver docs/01_estrategia_pruebas.md).
ITERACIONES_REPORTE = 400_000

app = FastAPI(title="Tienda ficticia - laboratorio de carga")


class Pedido(BaseModel):
    # strict=True: "5" o 5.0 no se aceptan, la cantidad debe ser un entero real
    producto_id: int = Field(strict=True)
    cantidad: int = Field(ge=1, le=10, strict=True)


def conectar():
    """Abre una conexión nueva por petición (simple y segura entre hilos)."""
    con = sqlite3.connect(DB, timeout=5)
    con.row_factory = sqlite3.Row
    return con


@app.get("/health")
def health():
    return {"estado": "ok"}


@app.get("/api/productos")
def listar_productos():
    with closing(conectar()) as con:
        filas = con.execute("SELECT id, nombre, precio FROM productos").fetchall()
    return [dict(f) for f in filas]


@app.post("/api/pedidos", status_code=201)
def crear_pedido(pedido: Pedido):
    # Si el JSON no cumple el modelo, FastAPI responde 422 automáticamente.
    with closing(conectar()) as con:
        existe = con.execute(
            "SELECT 1 FROM productos WHERE id = ?", (pedido.producto_id,)
        ).fetchone()
        if not existe:
            raise HTTPException(status_code=422, detail="El producto no existe")
        cur = con.execute(
            "INSERT INTO pedidos (producto_id, cantidad) VALUES (?, ?)",
            (pedido.producto_id, pedido.cantidad),
        )
        con.commit()
    return {"id": cur.lastrowid, "producto_id": pedido.producto_id,
            "cantidad": pedido.cantidad}


@app.get("/api/reporte")
def reporte():
    """Operación pesada simulada: cálculo de CPU puro = cuello de botella."""
    control = 0
    for i in range(ITERACIONES_REPORTE):
        control = (control + i * i) % 1_000_003
    with closing(conectar()) as con:
        total, unidades = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(cantidad), 0) FROM pedidos"
        ).fetchone()
    return {"pedidos": total, "unidades": unidades, "control": control}

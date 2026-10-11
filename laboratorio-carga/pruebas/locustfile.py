r"""Escenario de carga: usuarios virtuales que compran en la tienda ficticia.

Ejecutar en Windows (con la API encendida en otra terminal, desde
laboratorio-carga), todo en UNA sola línea:
    locust -f pruebas\locustfile.py --host http://127.0.0.1:8000 --headless
    --csv resultados\run --csv-full-history --html resultados\reporte.html
"""
import random

from locust import HttpUser, LoadTestShape, between, task

TIMEOUT = 5  # segundos: si la API tarda más, la petición cuenta como falla

# Pedidos que la API DEBE rechazar con 422 (caso CP-02)
PEDIDOS_INVALIDOS = [
    {"producto_id": 1, "cantidad": 0},        # cantidad menor que 1
    {"producto_id": 1, "cantidad": 11},       # cantidad mayor que 10
    {"producto_id": 1, "cantidad": 2.5},      # cantidad no entera
    {"producto_id": 1, "cantidad": "tres"},   # tipo incorrecto
    {"producto_id": 999, "cantidad": 1},      # producto inexistente
    {"cantidad": 1},                          # falta producto_id
]


class Cliente(HttpUser):
    """Un usuario virtual: elige tareas según su peso y espera entre acciones."""
    wait_time = between(0.5, 1.5)

    @task(5)
    def listar_productos(self):
        self.client.get("/api/productos", timeout=TIMEOUT)

    @task(3)
    def pedido_valido(self):
        pedido = {"producto_id": random.randint(1, 20),
                  "cantidad": random.randint(1, 10)}
        self.client.post("/api/pedidos", json=pedido, timeout=TIMEOUT)

    @task(1)
    def pedido_invalido(self):
        # Aquí el 422 es la respuesta CORRECTA, así que lo marcamos como éxito
        with self.client.post("/api/pedidos", json=random.choice(PEDIDOS_INVALIDOS),
                              name="POST /api/pedidos [inválido]",
                              timeout=TIMEOUT, catch_response=True) as r:
            if r.status_code == 422:
                r.success()
            elif r.status_code:  # llegó respuesta, pero no la esperada
                r.failure(f"Se esperaba 422 y llegó {r.status_code}")
            # status 0 = sin respuesta (timeout): Locust lo registra como falla

    @task(1)
    def reporte_pesado(self):
        self.client.get("/api/reporte", timeout=TIMEOUT)


class FasesDeCarga(LoadTestShape):
    """Controla cuántos usuarios hay en cada momento de la prueba."""
    # (nombre, usuarios, duración en segundos) -> total 210 s
    FASES = [
        ("F1 Normal", 10, 30),
        ("F2 Carga", 50, 30),
        ("F3 Alta", 100, 30),
        ("F4 Estrés", 200, 30),
        ("F5 Pico", 400, 30),
        ("F6 Recuperación", 10, 60),
    ]
    USUARIOS_POR_SEGUNDO = 100  # velocidad para subir/bajar usuarios

    def tick(self):
        t = self.get_run_time()
        fin = 0
        for _nombre, usuarios, duracion in self.FASES:
            fin += duracion
            if t < fin:
                return usuarios, self.USUARIOS_POR_SEGUNDO
        return None  # se acabaron las fases: Locust termina la prueba

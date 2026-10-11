# 05 · Guía para explicar el código

Diez líneas por archivo: qué hace y por qué. Con esto cualquier integrante del
grupo puede defender cualquier parte del laboratorio.

## `api\seed.py` — prepara los datos

1. Crea (o reinicia) el archivo de base de datos `api\tienda.db` junto al script.
2. Activa el modo **WAL** de SQLite, que permite leer mientras otro hilo escribe y evita bloqueos innecesarios.
3. Borra las tablas `pedidos` y `productos` si existen, para que **cada corrida parta del mismo estado**.
4. Crea `productos` (id, nombre, precio) y `pedidos` (id, producto, cantidad, fecha).
5. La tabla `pedidos` tiene un `CHECK` de cantidad entre 1 y 10, como segunda barrera además de la API.
6. Inserta 20 productos **ficticios** de papelería y tecnología con precios inventados.
7. Usa `executemany`, que inserta todos los productos en una sola operación.
8. Imprime cuántos productos quedaron y dónde está la base, como confirmación visual.
9. Se ejecuta **antes de cada prueba** (`python api\seed.py`), con la API detenida o recién iniciada.
10. Por qué: una prueba de rendimiento solo es comparable si los datos iniciales son siempre los mismos.

## `api\main.py` — la API bajo prueba

1. Crea una aplicación FastAPI con 4 endpoints: `/health`, `/api/productos`, `/api/pedidos` y `/api/reporte`.
2. Todos son **síncronos** (`def`): FastAPI los ejecuta en un pool de hilos dentro de **un solo proceso**.
3. Por el **GIL** de Python, solo un hilo usa la CPU a la vez, así que con 1 worker la saturación es real y fácil de explicar.
4. `conectar()` abre una conexión nueva a SQLite por petición, que es lo más simple y seguro entre hilos.
5. El modelo `Pedido` (Pydantic) exige `producto_id` entero y `cantidad` entera entre 1 y 10, con `strict=True` para no aceptar "5" ni 5.0.
6. Si el cuerpo no cumple el modelo, FastAPI responde **422** automáticamente, sin ejecutar nuestro código.
7. Si el producto no existe, respondemos 422 con `HTTPException` ("El producto no existe").
8. Un pedido válido se guarda con `INSERT` y `commit` y responde **201** con el id creado.
9. `/api/reporte` simula una operación costosa: un bucle de `ITERACIONES_REPORTE` (400.000) cálculos de CPU y luego una consulta de totales.
10. Ese reporte es el **cuello de botella** a propósito; su costo se calibró para que la degradación aparezca entre F3 y F5.

## `pruebas\locustfile.py` — el escenario de carga

1. Define un usuario virtual, `Cliente` (`HttpUser`), que espera entre 0,5 y 1,5 s entre acciones (`between`), como una persona real.
2. Cada petición tiene `timeout=5`: si la API tarda más, Locust la registra como **falla** (timeout).
3. Las tareas tienen **pesos** 5/3/1/1: listar productos, pedido válido, pedido inválido y reporte.
4. El pedido válido elige producto (1–20) y cantidad (1–10) al azar.
5. El pedido inválido elige uno de 6 cuerpos malos (cantidad 0, 11, 2.5, "tres", producto 999, sin producto).
6. En el inválido usamos `catch_response=True` porque el **422 es la respuesta correcta** y lo marcamos como éxito.
7. Si llega otro código (por ejemplo 500), lo marcamos como falla con el texto "Se esperaba 422 y llegó X".
8. Se registra con un nombre distinto, `POST /api/pedidos [inválido]`, para medirlo aparte.
9. `FasesDeCarga` (`LoadTestShape`) decide cuántos usuarios hay en cada segundo: 10, 50, 100, 200, 400 y 10 (30 s cada fase y 60 s la última).
10. Cuando se acaban las fases, `tick()` devuelve `None` y Locust termina solo. Así **una sola ejecución cubre los 5 casos de prueba**.

## `pruebas\analizar.py` — el análisis

1. Lee `resultados\run_stats_history.csv`, donde Locust guarda una fila por segundo, y se queda con la fila `Aggregated` (todas las peticiones).
2. Calcula el tiempo transcurrido de cada fila y la **asigna a su fase** según los inicios 0, 30, 60, 90, 120 y 150 s.
3. Pasa los totales acumulados de peticiones y fallas a cantidades por segundo con `diff()`.
4. Descarta los **primeros 10 s de cada fase**, porque Locust da el p95 de los últimos 10 s y al cambiar de fase todavía mezcla la anterior.
5. Por fase calcula usuarios, peticiones/s, p50, p95 (mediana de los valores por segundo) y % de errores.
6. Aplica los criterios: APROBADA si p95 < 500 ms y errores < 1 %; el **punto de degradación** es la primera fase con p95 > 1000 ms o errores > 5 %.
7. **Recuperación:** compara F6 con F1 (p95 ≤ 1,2 × p95 F1 y errores < 1 %) y mide en cuántos segundos el p95 volvió bajo el umbral.
8. **CP-02 y CP-04:** con `run_stats.csv` y `run_failures.csv` cuenta las respuestas 422 y 500 de los inválidos y clasifica las fallas en timeouts, 5xx, conexiones rechazadas u otras.
9. Escribe `resumen.csv` y `resumen.md` y genera `grafica.png` con 3 paneles (usuarios, p95, peticiones y errores por segundo), con las fases sombreadas y las no aprobadas en rojo.
10. Lee los CSV con UTF-8 y, si falla, con cp1252, porque en Windows Locust los guarda con la codificación del sistema.

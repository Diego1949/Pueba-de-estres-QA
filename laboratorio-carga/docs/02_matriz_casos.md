# 02 · Matriz de casos de prueba

Los 5 casos son de tipo **Sistema** y se automatizan con **la misma ejecución de
Locust**: una sola corrida de 210 s cubre las 6 fases y `pruebas\analizar.py`
evalúa los criterios de cada caso. Los resultados son los de la corrida oficial
del 10 de octubre de 2026 (`ITERACIONES_REPORTE = 400_000`). La misma matriz
está en [02_matriz_casos.csv](02_matriz_casos.csv) para abrirla en Excel.

**Comando de ejecución en Windows (común a los 5 casos)**, en PowerShell o CMD,
desde `laboratorio-carga`, con el entorno activado y la API encendida:

```powershell
locust -f pruebas\locustfile.py --host http://127.0.0.1:8000 --headless --csv resultados\run --csv-full-history --html resultados\reporte.html
python pruebas\analizar.py
```

**Precondiciones comunes:** entorno instalado (`pip install -r requirements.txt`) y
activado (`.venv\Scripts\Activate.ps1` en PowerShell o `.venv\Scripts\activate.bat`
en CMD), BD reiniciada con `python api\seed.py` (20 productos, 0 pedidos), API
iniciada con `uvicorn api.main:app --workers 1 --port 8000 --no-access-log` y
`GET /health` respondiendo 200.

## Resumen

| Identificador | Nombre | Tipo de prueba | Resultado obtenido (clave) | Estado |
|---|---|---|---|---|
| CP-01 | Carga normal (flujo exitoso) | Sistema | F1: p95 60 ms, 0 % errores | Aprobado |
| CP-02 | Datos inválidos bajo carga (error funcional) | Sistema | 1448 de 1448 respondieron 422; 0 respondieron 500 | Aprobado |
| CP-03 | Carga escalonada e identificación del punto de degradación | Sistema | Degradación en F4 (p95 2100 ms) | Aprobado |
| CP-04 | Estrés y pico (falla técnica: timeouts/5xx) | Sistema | 143 timeouts, 0 errores 5xx; la API no se cayó | Aprobado |
| CP-05 | Recuperación tras retirar la carga | Sistema | F6: p95 50 ms ≤ 72 ms, 0 % errores | Aprobado |

---

## CP-01 · Carga normal (flujo exitoso)

| Campo | Contenido |
|---|---|
| **Identificador** | CP-01 |
| **Nombre** | Carga normal (flujo exitoso) |
| **Tipo de prueba** | Sistema |
| **Objetivo** | Verificar que, con la carga normal de 10 usuarios, los flujos principales (listar productos, crear pedido, generar reporte) responden correctamente y dentro del criterio de calidad. |
| **Componentes involucrados** | Locust (usuario `Cliente`), Uvicorn (1 worker), FastAPI: `GET /api/productos`, `POST /api/pedidos`, `GET /api/reporte`; SQLite |
| **Precondiciones** | Precondiciones comunes (BD sembrada, API activa, `/health` = 200) |
| **Datos de entrada** | Fase F1: 10 usuarios durante 30 s, espera de 0,5 a 1,5 s; pedidos válidos aleatorios (`producto_id` 1–20, `cantidad` 1–10) |
| **Procedimiento** | 1. Ejecutar el comando de Locust. 2. Ejecutar `python pruebas\analizar.py`. 3. Revisar la fila "F1 Normal" de `resultados\resumen.md`. |
| **Resultado esperado** | F1 APROBADA: p95 < 500 ms y errores < 1 % |
| **Resultado obtenido** | F1: 10 usuarios, 9,7 pet/s, p50 22 ms, **p95 60 ms**, **0,0 % errores** → APROBADA |
| **Evidencia** | `resultados\resumen.md` (fila F1), `resultados\grafica.png`, `resultados\reporte.html`, `resultados\run_stats_history.csv` |
| **Estado** | ✅ Aprobado |

## CP-02 · Datos inválidos bajo carga (error funcional)

| Campo | Contenido |
|---|---|
| **Identificador** | CP-02 |
| **Nombre** | Datos inválidos bajo carga (error funcional) |
| **Tipo de prueba** | Sistema |
| **Objetivo** | Verificar que la API rechaza con 422 los pedidos inválidos durante toda la prueba, incluso en estrés y pico, y que nunca responde 500. |
| **Componentes involucrados** | Locust (tarea `pedido_invalido`), FastAPI `POST /api/pedidos` (validación del modelo `Pedido` y verificación del producto en SQLite) |
| **Precondiciones** | Precondiciones comunes |
| **Datos de entrada** | 6 cuerpos inválidos elegidos al azar: `cantidad` 0, `cantidad` 11, `cantidad` 2.5, `cantidad` "tres", `producto_id` 999 (no existe), sin `producto_id`. Peso 1 de 10 en la mezcla de tareas, presente en las 6 fases. |
| **Procedimiento** | 1. Ejecutar el comando de Locust. Las peticiones se registran como "POST /api/pedidos [inválido]": un 422 se marca como éxito y cualquier otro código como falla ("Se esperaba 422 y llegó X"). 2. Ejecutar `analizar.py`, que cuenta los códigos con `run_stats.csv` y `run_failures.csv`. 3. Revisar la línea CP-02 de `resumen.md`. |
| **Resultado esperado** | El 100 % de las respuestas a pedidos inválidos es 422 y ninguna es 500 |
| **Resultado obtenido** | **1448 inválidas enviadas: 1448 respondieron 422, 0 respondieron 500**, 0 otro código, 0 sin respuesta. Incluso en F5 la validación siguió respondiendo (p95 de las inválidas en F5: 1200 ms). |
| **Evidencia** | `resultados\resumen.md` (línea CP-02), `resultados\run_stats.csv` (fila "POST /api/pedidos [inválido]", 0 fallas), `resultados\run_failures.csv` |
| **Estado** | ✅ Aprobado |

## CP-03 · Carga escalonada e identificación del punto de degradación

| Campo | Contenido |
|---|---|
| **Identificador** | CP-03 |
| **Nombre** | Carga escalonada e identificación del punto de degradación |
| **Tipo de prueba** | Sistema |
| **Objetivo** | Aumentar la carga por escalones (10 → 50 → 100 → 200 usuarios) e identificar la primera fase en que el sistema se degrada. |
| **Componentes involucrados** | Locust (`FasesDeCarga`, una `LoadTestShape`), los 4 endpoints, Uvicorn con 1 worker, SQLite |
| **Precondiciones** | Precondiciones comunes |
| **Datos de entrada** | F1 10, F2 50, F3 100 y F4 200 usuarios, 30 s cada fase; mezcla de tareas 5/3/1/1 |
| **Procedimiento** | 1. Ejecutar el comando de Locust. 2. Ejecutar `analizar.py`, que calcula por fase usuarios, pet/s, p50, p95 y % de errores. 3. Aplicar la regla: el punto de degradación es la primera fase con p95 > 1000 ms o errores > 5 %. |
| **Resultado esperado** | F1 y F2 aprobadas y un punto de degradación identificado entre F3 y F5 |
| **Resultado obtenido** | p95 por fase: F1 60 ms, F2 155 ms, F3 125 ms (las tres APROBADAS), **F4 2100 ms** (errores 0,74 %). **Punto de degradación: F4 Estrés.** El rendimiento se estancó en ~157 pet/s en F4 y ~169 pet/s en F5, que es la capacidad máxima con 1 worker. |
| **Evidencia** | `resultados\resumen.md`, `resultados\resumen.csv`, `resultados\grafica.png` (línea roja punteada) |
| **Estado** | ✅ Aprobado |

## CP-04 · Estrés y pico (falla técnica: timeouts/5xx)

| Campo | Contenido |
|---|---|
| **Identificador** | CP-04 |
| **Nombre** | Estrés y pico (falla técnica: timeouts/5xx) |
| **Tipo de prueba** | Sistema |
| **Objetivo** | Llevar la API más allá de su capacidad (200 y 400 usuarios) para provocar, registrar y clasificar fallas técnicas (timeouts, 5xx) y verificar que el servicio no se cae. |
| **Componentes involucrados** | Locust (timeout de 5 s por petición), Uvicorn (1 worker, pool de hilos), `GET /api/reporte` (cuello de botella), `POST /api/pedidos` (escrituras en SQLite) |
| **Precondiciones** | Precondiciones comunes; corrida continua desde F1 |
| **Datos de entrada** | F4 con 200 usuarios y F5 con 400 usuarios, 30 s cada una; timeout de 5 s |
| **Procedimiento** | 1. Ejecutar el comando de Locust. 2. Ejecutar `analizar.py`, que clasifica las fallas de `run_failures.csv` en timeouts, 5xx, conexiones rechazadas y otras y comprueba que la API siga respondiendo en F6. 3. Revisar la línea CP-04 de `resumen.md` y el panel de errores de la gráfica. |
| **Resultado esperado** | Bajo estrés aparecen fallas técnicas registradas y clasificadas (timeouts > 5 s y/o 5xx), y la API no se cae: sigue respondiendo al retirar la carga. |
| **Resultado obtenido** | F4: p95 2100 ms y 0,74 % de errores. F5: p95 2600 ms y 1,75 % de errores; el p95 por segundo llegó a 5000 ms. **Total: 143 timeouts (> 5 s), 0 errores 5xx, 0 conexiones rechazadas, 0 otras**, todos en `POST /api/pedidos`. La API siguió respondiendo en F6. |
| **Evidencia** | `resultados\run_failures.csv`, `resultados\resumen.md` (línea CP-04), `resultados\grafica.png` (panel inferior), `resultados\reporte.html` |
| **Estado** | ✅ Aprobado (falla técnica provocada y documentada, sin caída del servicio) |

## CP-05 · Recuperación tras retirar la carga

| Campo | Contenido |
|---|---|
| **Identificador** | CP-05 |
| **Nombre** | Recuperación tras retirar la carga |
| **Tipo de prueba** | Sistema |
| **Objetivo** | Verificar que, al bajar de 400 a 10 usuarios, la API vuelve a su desempeño normal sin reiniciarla. |
| **Componentes involucrados** | Locust (fase F6), Uvicorn, FastAPI (los 4 endpoints) y SQLite |
| **Precondiciones** | Precondiciones comunes; F5 (pico) ejecutada justo antes en la misma corrida, sin reiniciar la API |
| **Datos de entrada** | F6 con 10 usuarios durante 60 s; línea base: p95 de F1 |
| **Procedimiento** | 1. Ejecutar el comando de Locust. 2. Ejecutar `analizar.py`, que compara F6 con F1. 3. Revisar las líneas "Recuperación OK" y "Tiempo hasta recuperar" de `resumen.md`. |
| **Resultado esperado** | En F6: p95 ≤ 1,2 × p95 de F1 y errores < 1 % |
| **Resultado obtenido** | **p95 F6 = 50 ms ≤ 72 ms** (1,2 × 60 ms) y **0,0 % de errores** en el tramo estable. El p95 por segundo bajó del umbral 28 s después de iniciar F6 (incluye la ventana de 10 s de Locust). Los 32 timeouts de los primeros 5 s de F6 eran peticiones enviadas durante F5. |
| **Evidencia** | `resultados\resumen.md`, `resultados\grafica.png` (zona F6), `resultados\run_stats_history.csv` |
| **Estado** | ✅ Aprobado |

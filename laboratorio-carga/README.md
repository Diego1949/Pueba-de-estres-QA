# Laboratorio de pruebas de carga y estrés

Laboratorio **muy simple** para una exposición de QA: sometemos una API funcional
a distintos niveles de demanda, identificamos el **punto de degradación** y
verificamos que el sistema se **recupera** cuando se retira la carga.

Todo es local y gratuito: sin Docker, sin nube, solo contra `127.0.0.1` (localhost)
y con datos ficticios. **Preparado y probado en Windows 11** (PowerShell y CMD).

| Pieza | Herramienta |
|---|---|
| API bajo prueba | FastAPI + uvicorn (1 solo worker) |
| Base de datos | SQLite (archivo `api\tienda.db`) |
| Generador de carga | Locust (modo headless, sin interfaz) |
| Análisis y gráfica | pandas + matplotlib |

## Estructura

```
laboratorio-carga\
  api\main.py            -> la API (4 endpoints)
  api\seed.py            -> crea la BD con 20 productos ficticios
  pruebas\locustfile.py  -> escenario de carga con 6 fases
  pruebas\analizar.py    -> lee resultados y genera resumen y gráfica
  resultados\            -> CSV de Locust, reporte.html, resumen.csv, resumen.md, grafica.png
  docs\                  -> documentos entregables (estrategia, matriz, análisis...)
  requirements.txt
```

## Endpoints de la API

| Método y ruta | Qué hace |
|---|---|
| `GET /health` | Responde `{"estado": "ok"}` si la API está viva |
| `GET /api/productos` | Lista los 20 productos (lectura simple) |
| `POST /api/pedidos` | Crea un pedido. Valida `producto_id` existente y `cantidad` entera de 1 a 10; si no, responde **422** |
| `GET /api/reporte` | Operación pesada simulada (cálculo de CPU): es el **cuello de botella** |

## Fases de la prueba (210 s en total)

| Fase | Usuarios | Duración |
|---|---|---|
| F1 Normal | 10 | 30 s |
| F2 Carga | 50 | 30 s |
| F3 Alta | 100 | 30 s |
| F4 Estrés | 200 | 30 s |
| F5 Pico | 400 | 30 s |
| F6 Recuperación | 10 | 60 s |

Cada usuario virtual espera entre 0,5 y 1,5 s entre acciones y elige tareas con
estos pesos: listar productos (5), pedido válido (3), pedido inválido (1, se
espera 422) y reporte pesado (1). Timeout de 5 s por petición.

---

## Paso a paso en Windows

**Requisitos**

- Windows 10 u 11.
- **Python 3.11 o superior**, instalado desde python.org. Compruébelo con
  `python --version`. Si Windows no reconoce `python` o abre la Microsoft Store,
  use `py --version`, y en el paso de crear el entorno escriba `py -m venv .venv`
  en lugar de `python -m venv .venv`.
- **Dos terminales** abiertas en la carpeta `laboratorio-carga`. Un atajo: abra la
  carpeta en el Explorador de archivos, escriba `powershell` en la barra de
  direcciones y presione Enter.

Los comandos son iguales en PowerShell y en CMD. **Solo cambia la línea que activa
el entorno virtual:**

| Terminal | Activar el entorno |
|---|---|
| PowerShell (recomendada) | `.venv\Scripts\Activate.ps1` |
| Símbolo del sistema (CMD) | `.venv\Scripts\activate.bat` |

Cuando el entorno está activo, la línea de comandos empieza con `(.venv)`.

### Terminal 1: preparar e iniciar la API (PowerShell)

```powershell
cd laboratorio-carga
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python api\seed.py
uvicorn api.main:app --workers 1 --port 8000 --no-access-log
```

- `python -m venv .venv` y `pip install ...` **solo se hacen la primera vez**.
- Si PowerShell muestra un error rojo al activar ("la ejecución de scripts está
  deshabilitada"), ejecute una sola vez
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, responda `S` (o `Y` si
  Windows está en inglés) y vuelva a activar. Otra opción es usar CMD.
- La API queda corriendo cuando aparece `Uvicorn running on http://127.0.0.1:8000`.
  Compruébelo en el navegador: <http://127.0.0.1:8000/health>. La documentación
  automática está en <http://127.0.0.1:8000/docs>.

### Terminal 2: correr la carga y analizar (PowerShell)

```powershell
cd laboratorio-carga
.venv\Scripts\Activate.ps1
locust -f pruebas\locustfile.py --host http://127.0.0.1:8000 --headless --csv resultados\run --csv-full-history --html resultados\reporte.html
python pruebas\analizar.py
```

- El comando de `locust` es **una sola línea**; cópielo completo.
- La prueba dura unos **3 minutos y medio** y termina sola.
- Al final Locust muestra `exit code 1`. **Es lo esperado**: Locust devuelve 1
  cuando hubo fallas, y en esta prueba las provocamos a propósito (fases de
  estrés y pico).

Para ver los resultados:

```powershell
start resultados\grafica.png
start resultados\reporte.html
```

### Las mismas terminales en CMD (Símbolo del sistema)

Terminal 1:

```bat
cd laboratorio-carga
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python api\seed.py
uvicorn api.main:app --workers 1 --port 8000 --no-access-log
```

Terminal 2:

```bat
cd laboratorio-carga
.venv\Scripts\activate.bat
locust -f pruebas\locustfile.py --host http://127.0.0.1:8000 --headless --csv resultados\run --csv-full-history --html resultados\reporte.html
python pruebas\analizar.py
start resultados\grafica.png
```

### Detener y repetir la demo

1. En la terminal 1 presione `Ctrl + C` para detener la API.
2. Siembre de nuevo la BD e inicie otra vez la API, para que cada corrida parta
   del mismo estado:
   ```powershell
   python api\seed.py
   uvicorn api.main:app --workers 1 --port 8000 --no-access-log
   ```
3. En la terminal 2 repita el comando de `locust` y luego `python pruebas\analizar.py`.
   Los archivos de `resultados\` se sobrescriben.

Si al iniciar la API aparece `[Errno 10048] error while attempting to bind on address`
(puerto 8000 en uso), quedó otra API abierta: ciérrela con `Ctrl + C` en su
terminal o cierre esa ventana.

### Antes de la demo (ambiente controlado)

Las métricas dependen del equipo. En la calibración observamos que el mismo
escenario cambia bastante si el equipo está ocupado, así que antes de exponer:

- Conecte el portátil a la corriente y cierre programas pesados (navegador con
  muchas pestañas, videollamadas, etc.).
- Si acaba de instalar las dependencias, espere unos minutos: el antivirus de
  Windows revisa los archivos nuevos de `.venv` y consume CPU.
- Haga una corrida de ensayo completa el mismo día. El punto de degradación
  puede variar entre F4 y F5 de una corrida a otra (ver
  [docs/03_analisis_resultados.md](docs/03_analisis_resultados.md)).

---

## Qué significa cada opción del comando de Locust

| Opción | Para qué |
|---|---|
| `-f pruebas\locustfile.py` | Archivo con el escenario y las fases |
| `--host http://127.0.0.1:8000` | API bajo prueba (localhost). Se usa la IP y no la palabra `localhost` porque en Windows esta última puede añadir ~2 s a cada conexión nueva |
| `--headless` | Sin interfaz web: corre las fases y termina solo |
| `--csv resultados\run` | Guarda `run_stats.csv`, `run_failures.csv`, `run_exceptions.csv` y `run_stats_history.csv` |
| `--csv-full-history` | El historial guarda una fila por segundo con el p50/p95 de los últimos 10 s (necesario para separar por fase) |
| `--html resultados\reporte.html` | Reporte visual de Locust |

## Resultados que se generan

| Archivo | Contenido |
|---|---|
| `resultados\run_stats_history.csv` | Métricas segundo a segundo (fuente del análisis) |
| `resultados\run_stats.csv` / `run_failures.csv` | Totales por endpoint y detalle de errores |
| `resultados\reporte.html` | Reporte de Locust (abrir en el navegador) |
| `resultados\resumen.csv` / `resumen.md` | Tabla por fase con usuarios, peticiones/s, p50, p95, % errores y estado |
| `resultados\grafica.png` | 3 paneles: usuarios, p95 y peticiones/errores por segundo, con las fases sombreadas |

## Criterios de aprobación

- **Fase APROBADA:** p95 < 500 ms y errores < 1 %.
- **Punto de degradación:** primera fase con p95 > 1000 ms o errores > 5 %.
- **Recuperación OK:** en F6 el p95 vuelve a ser ≤ 1,2 × p95 de F1 y errores < 1 %.
- **Validación (CP-02):** las peticiones inválidas responden 422 y ninguna 500.

## Documentos entregables (carpeta `docs\`)

| Documento | Contenido |
|---|---|
| [01_estrategia_pruebas.md](docs/01_estrategia_pruebas.md) | Objetivo, componentes, riesgos, alcance, ambiente, datos, herramientas, criterios y calibración |
| [02_matriz_casos.md](docs/02_matriz_casos.md) / [.csv](docs/02_matriz_casos.csv) | Los 5 casos de prueba de sistema con su resultado real |
| [03_analisis_resultados.md](docs/03_analisis_resultados.md) | Interpretación, hallazgos, conclusiones y mejoras |
| [04_referencias.md](docs/04_referencias.md) | Documentación oficial de Locust, FastAPI, Uvicorn y SQLite |
| [05_guia_para_explicar_el_codigo.md](docs/05_guia_para_explicar_el_codigo.md) | 10 líneas por archivo para defender el código |

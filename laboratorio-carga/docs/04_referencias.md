# 04 · Referencias

Solo documentación oficial de las herramientas usadas. Todas las URLs se
verificaron el 10 de octubre de 2026.

## Locust (generador de carga) · versión usada 2.46.7

| Tema | URL |
|---|---|
| Documentación oficial (inicio) | https://docs.locust.io/en/stable/ |
| Escribir un locustfile: `HttpUser`, `@task`, `wait_time`, `catch_response` | https://docs.locust.io/en/stable/writing-a-locustfile.html |
| Configuración y opciones (`--headless`, `--csv`, `--csv-full-history`, `--html`) | https://docs.locust.io/en/stable/configuration.html |
| Formas de carga personalizadas (`LoadTestShape`) | https://docs.locust.io/en/stable/configuration.html#custom-load-shapes |
| Ejecutar sin interfaz web (modo headless) | https://docs.locust.io/en/stable/running-without-web-ui.html |

## FastAPI (framework de la API) · versión usada 0.143.0

| Tema | URL |
|---|---|
| Documentación oficial (inicio) | https://fastapi.tiangolo.com/ |
| `async def` frente a `def`: los endpoints `def` corren en un pool de hilos | https://fastapi.tiangolo.com/async/ |
| Cuerpo de la petición y validación con modelos | https://fastapi.tiangolo.com/tutorial/body/ |
| Manejo de errores (`HTTPException`, respuestas 422) | https://fastapi.tiangolo.com/tutorial/handling-errors/ |
| Workers del servidor (varios procesos) | https://fastapi.tiangolo.com/deployment/server-workers/ |

## Uvicorn (servidor ASGI) · versión usada 0.54.0

| Tema | URL |
|---|---|
| Documentación oficial (inicio) | https://uvicorn.dev/ |
| Opciones (`--workers`, `--port`, `--no-access-log`, `--limit-concurrency`) | https://uvicorn.dev/settings/ |
| Despliegue | https://uvicorn.dev/deployment/ |

## SQLite (base de datos) · versión usada 3.45.3

| Tema | URL |
|---|---|
| Documentación oficial (índice) | https://www.sqlite.org/docs.html |
| Modo WAL (*Write-Ahead Logging*), lectores y un escritor | https://www.sqlite.org/wal.html |
| Bloqueos y concurrencia | https://www.sqlite.org/lockingv3.html |
| Instrucciones PRAGMA (`journal_mode`) | https://www.sqlite.org/pragma.html |

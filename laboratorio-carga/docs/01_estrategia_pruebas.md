# 01 · Estrategia de pruebas de rendimiento

**Proyecto:** Laboratorio de pruebas de carga y estrés · **Nivel de prueba:** Sistema
**Fecha de la ejecución oficial:** 10 de octubre de 2026 · **Herramienta principal:** Locust 2.46.7

---

## 1. Objetivo

Someter una API funcional a distintos niveles de demanda (normal, carga, alta,
estrés y pico) para **identificar el punto de degradación** y **verificar que el
sistema se recupera** cuando se retira la carga, sin reiniciarlo.

Preguntas que responde la prueba:

1. ¿Cuántos usuarios soporta la API cumpliendo el criterio de calidad (p95 < 500 ms y errores < 1 %)?
2. ¿En qué fase empieza a degradarse (p95 > 1000 ms o errores > 5 %)?
3. ¿Qué tipo de falla aparece bajo estrés: lentitud, timeouts o errores 5xx?
4. ¿La validación de datos sigue funcionando bajo carga (422, nunca 500)?
5. ¿Vuelve el sistema a su desempeño normal al bajar la carga?

## 2. Componentes del sistema bajo prueba

| Componente | Rol | Detalle |
|---|---|---|
| API FastAPI (`api\main.py`) | Sistema bajo prueba | 4 endpoints síncronos (`def`) |
| Uvicorn | Servidor web | **1 solo worker** en `127.0.0.1:8000`, sin log de accesos |
| SQLite (`api\tienda.db`) | Base de datos | Tablas `productos` (20 filas) y `pedidos`; modo WAL |
| `GET /health` | Verificación de vida | Precondición de la prueba |
| `GET /api/productos` | Lectura simple | Lista los 20 productos |
| `POST /api/pedidos` | Escritura con validación | Exige `producto_id` existente y `cantidad` entera 1–10; si no, responde 422 |
| `GET /api/reporte` | **Cuello de botella** | Cálculo de CPU de 400.000 iteraciones más una consulta de totales |
| Locust (`pruebas\locustfile.py`) | Generador de carga | Usuarios virtuales con 6 fases (`LoadTestShape`) |
| `pruebas\analizar.py` | Análisis | Métricas por fase, criterios, `resumen.md` y `grafica.png` |

**Por qué se satura:** con un solo worker hay un solo proceso de Python. FastAPI
ejecuta los endpoints `def` en un pool de hilos, pero por el GIL de Python solo un
hilo calcula a la vez. Cuando llegan muchos reportes, la CPU de ese proceso se
llena y **todas** las peticiones (incluso las simples) esperan su turno.

## 3. Puntos críticos a validar

1. **Latencia p95 por fase.** Es el tiempo bajo el cual queda el 95 % de las peticiones y refleja la experiencia de casi todos los usuarios.
2. **Tasa de errores por fase:** timeouts (> 5 s), errores 5xx, conexiones rechazadas y respuestas inesperadas.
3. **Rendimiento (peticiones/s).** Hay que ver si crece con los usuarios o se estanca, porque estancarse significa que se alcanzó la capacidad máxima.
4. **Validación funcional bajo carga.** Los pedidos inválidos deben responder 422 incluso en estrés y nunca 500.
5. **Efecto del cuello de botella.** Hay que ver cuánto frena `/api/reporte` a los demás endpoints.
6. **Escrituras concurrentes en SQLite.** SQLite acepta un solo escritor a la vez.
7. **Recuperación.** En F6, el p95 y los errores deben volver al nivel de F1.

## 4. Riesgos

| # | Riesgo | Tipo | Mitigación en el laboratorio |
|---|---|---|---|
| R1 | La CPU se satura por `/api/reporte` y frena a todos los endpoints | Producto | Es el comportamiento que se quiere observar; se mide por fase |
| R2 | Contención de escrituras en SQLite (un escritor a la vez) | Producto | Modo WAL; se mide el p95 de `POST /api/pedidos` |
| R3 | El servidor sigue procesando peticiones que el cliente ya abandonó por timeout, lo que retrasa la recuperación | Producto | Se mide el tiempo de recuperación en F6 |
| R4 | El generador de carga corre en la misma máquina y compite por CPU | Prueba | Locust en un solo proceso y la API sin log de accesos; se documenta como limitación |
| R5 | Variabilidad del ambiente: frecuencia de la CPU del portátil, antivirus, otros programas | Prueba | Varias corridas de calibración y recomendaciones de ambiente en el README |
| R6 | Locust reporta p50/p95 de una ventana móvil de 10 s, lo que mezcla fases en los cambios | Medición | Cada fase se mide sin sus primeros 10 s (sección 10) |
| R7 | Datos residuales de corridas anteriores | Prueba | `seed.py` reinicia la BD antes de cada corrida |

## 5. Alcance y exclusiones

**Dentro del alcance**

- Pruebas de **sistema** orientadas al rendimiento: carga normal, carga escalonada, estrés, pico y recuperación.
- Validación funcional de `POST /api/pedidos` **bajo carga** (respuestas 422).
- Los 4 endpoints de la API, ejecutados de punta a punta (HTTP → FastAPI → SQLite).

**Fuera del alcance (exclusiones)**

- Pruebas de seguridad, autenticación y autorización (la API no tiene).
- Pruebas de resistencia de larga duración (*soak*, horas) y de volumen de datos.
- Escalado horizontal, varios workers, balanceadores, Docker o nube.
- Latencia de red real (todo corre en `127.0.0.1`).
- Interfaz de usuario y navegadores.
- Pruebas unitarias y de integración por componente.
- Datos reales o personales: todos los datos son ficticios.

## 6. Ambiente de pruebas

| Elemento | Valor real de la ejecución |
|---|---|
| Equipo | Portátil AMD Ryzen 7 5825U (8 núcleos / 16 hilos, 2,0 GHz base), conectado a la corriente |
| Sistema operativo | Windows 11 Home Single Language, plan de energía "Equilibrado" |
| Python | 3.12.6 (entorno virtual `.venv`) |
| Versiones | FastAPI 0.143.0 · Uvicorn 0.54.0 · Locust 2.46.7 · pandas 3.0.6 · matplotlib 3.11.2 · SQLite 3.45.3 |
| Servidor | `uvicorn api.main:app --workers 1 --port 8000 --no-access-log` |
| Destino de la carga | `http://127.0.0.1:8000` (localhost) |
| Generador | Locust headless en la misma máquina, 1 proceso |
| Terminales | Comandos para Windows, validados de punta a punta en **PowerShell** (corrida oficial) y en **CMD** (corrida de validación) |

## 7. Datos de prueba

- **Productos:** 20 productos ficticios de papelería y tecnología con precios en pesos, creados por `api\seed.py`.
- **Estado inicial:** la BD se reinicia antes de cada corrida (0 pedidos).
- **Pedidos válidos:** `producto_id` aleatorio entre 1 y 20 y `cantidad` aleatoria entre 1 y 10.
- **Pedidos inválidos (6 variantes):** `cantidad` 0, `cantidad` 11, `cantidad` 2.5,
  `cantidad` "tres", `producto_id` 999 (no existe) y cuerpo sin `producto_id`.
- **Mezcla de tareas por usuario** (pesos): listar productos 5, pedido válido 3,
  pedido inválido 1, reporte 1. La espera entre acciones es aleatoria, de 0,5 a 1,5 s.

## 8. Dependencias reales y simuladas

| Dependencia | ¿Real o simulada? | Comentario |
|---|---|---|
| Servidor HTTP (Uvicorn) y framework (FastAPI) | Real | Mismo software que se usaría en producción |
| Base de datos SQLite | Real | Archivo en disco; lecturas y escrituras reales |
| Red | Real, pero local | Interfaz *loopback*, sin latencia de Internet |
| CPU del servidor | Real | Es el recurso que se agota |
| Reporte pesado | **Simulada** | Un bucle de cálculo representa una consulta o reporte costoso |
| Usuarios | **Simulada** | Usuarios virtuales de Locust |
| Datos | **Simulada** | Productos y pedidos ficticios |
| Servicios externos (pagos, inventario, correo) | No existen | Excluidos: la API no los usa |

## 9. Herramientas

| Herramienta | Uso |
|---|---|
| Locust | Generar la carga por fases (`LoadTestShape`), medir tiempos y exportar CSV y reporte HTML |
| FastAPI + Uvicorn | Construir y servir la API bajo prueba |
| SQLite | Persistir productos y pedidos |
| pandas | Leer los CSV, asignar cada segundo a su fase y calcular métricas |
| matplotlib | Generar `grafica.png` |
| Navegador o curl | Prueba de humo inicial (`/health`, `/docs`) |

## 10. Criterios de aprobado / fallido

**Cómo se mide cada fase.** Locust guarda cada segundo una fila con el p50/p95 de
los últimos 10 s. `analizar.py` asigna cada fila a su fase por tiempo transcurrido
y **descarta los primeros 10 s de cada fase**, por dos motivos: la ventana de
Locust aún contiene datos de la fase anterior, y subir o bajar usuarios tarda
unos segundos. En el tramo restante calcula usuarios, peticiones/s, % de errores
y el p50/p95, que es la mediana de los valores por segundo.

| Criterio | Regla |
|---|---|
| Fase APROBADA | p95 < 500 ms **y** errores < 1 % |
| Punto de degradación | Primera fase con p95 > 1000 ms **o** errores > 5 % |
| Recuperación OK | En F6, p95 ≤ 1,2 × p95 de F1 **y** errores < 1 % |
| Validación (CP-02) | Todas las respuestas a pedidos inválidos son 422; ninguna 500 |

**Criterios de inicio:** BD sembrada, `GET /health` responde 200 y la API corre con 1 worker.
**Criterios de fin:** Locust completa las 6 fases (210 s) y `analizar.py` genera `resumen.md` y `grafica.png`.
**Criterios por caso:** ver [02_matriz_casos.md](02_matriz_casos.md).

## 11. Escenario de carga

| Fase | Usuarios | Duración | Propósito |
|---|---|---|---|
| F1 Normal | 10 | 30 s | Línea base |
| F2 Carga | 50 | 30 s | Carga esperada |
| F3 Alta | 100 | 30 s | Carga alta |
| F4 Estrés | 200 | 30 s | Por encima de lo esperado |
| F5 Pico | 400 | 30 s | Pico repentino |
| F6 Recuperación | 10 | 60 s | Retirar la carga y observar la vuelta a la normalidad |

Los usuarios se suben y bajan a 100 por segundo. Cada petición tiene un timeout de 5 s.

## 12. Calibración del cuello de botella

Según el enunciado, solo se ajustó la carga de `/api/reporte` (constante
`ITERACIONES_REPORTE` en `api\main.py`); las fases no se tocaron. Se buscaba que
F1 y F2 fueran estables, que la degradación apareciera entre F3 y F5 y que F6
mostrara recuperación. Cada calibración fue una corrida completa de 3,5 minutos.
Estos son los datos reales (p95 en ms):

| # | Iteraciones | Estado del equipo | F1 | F2 | F3 | F4 | F5 | F6 | Degradación | Recuperación |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 200.000 | Recién instaladas las dependencias (antivirus activo) | 39 | 63 | 320 | 450 | 2000 | 40 | F5 | Sí |
| 2 | 300.000 | Ídem | 60 | 135 | 270 | 1100 | 2850 | 68 | F4 | Sí |
| 3 | 400.000 | Ídem | 51 | 160 | 415 | 1450 | 3900 | 63 | F4 | No (63 > 61) |
| 4 | 350.000 | Interferencia externa durante F2 | 34 | 775 | 210 | 1300 | 3150 | 60 | F4 | No (60 > 41) |
| 5 | 250.000 | Estable | 28 | 43 | 67 | 160 | 1300 | 32 | F5 | Sí |
| 6 | 300.000 | Estable | 32 | 52 | 120 | 230 | 1800 | 32 | F5 | Sí |
| 7 | 400.000 | Estable | 50 | 70 | 265 | 835 | 3600 | 48 | F5 | Sí |
| **8** | **400.000** | **Estable (corrida oficial, PowerShell)** | **60** | **155** | **125** | **2100** | **2600** | **50** | **F4** | **Sí** |
| 9 | 400.000 | Validación de los comandos en CMD (después de la oficial) | 66 | 200 | 620 | 2100 | 5150 | 71 | F4 | Sí (71 ≤ 79) |

**Decisión: 400.000 iteraciones** (≈ 35–50 ms por reporte con el equipo en reposo).
Con el equipo estable, F1 a F3 aprueban, la degradación aparece entre F4 y F5,
F5 produce timeouts que alimentan el caso CP-04 y F6 se recupera (corridas 7 y 8).
Con 250.000 o 300.000 iteraciones la degradación llegaba recién en F5 y con muy
pocas fallas técnicas.

**Lecciones de la calibración.**

- El ambiente pesa tanto como el código. Las corridas 1 a 4 fueron más lentas
  porque el equipo estaba ocupado: el antivirus revisaba los archivos recién
  instalados, y en la corrida 4 hubo una interferencia externa de unos 20 s en
  F2. Cuando la CPU trabaja más tiempo saturada, el portátil también baja su
  frecuencia, y entonces F6 queda más lenta que F1.
- Con la misma configuración (corridas 7 y 8), F4 dio 835 ms en una corrida y
  2100 ms en la otra. El punto de degradación está en la frontera entre F4 y F5,
  así que conviene repetir la prueba antes de concluir.

# Resumen de la prueba de carga

| Fase | Usuarios | Peticiones/s | p50 (ms) | p95 (ms) | % errores | Estado |
|---|---|---|---|---|---|---|
| F1 Normal | 10 | 9.7 | 22 | 60 | 0.0 | APROBADA |
| F2 Carga | 50 | 47.9 | 24 | 155 | 0.0 | APROBADA |
| F3 Alta | 100 | 94.8 | 34 | 125 | 0.0 | APROBADA |
| F4 Estrés | 200 | 156.6 | 170 | 2100 | 0.74 | NO APROBADA |
| F5 Pico | 400 | 168.7 | 1200 | 2600 | 1.75 | NO APROBADA |
| F6 Recuperación | 10 | 9.8 | 8 | 50 | 0.0 | APROBADA |

Criterio: fase APROBADA si p95 < 500 ms y errores < 1 %. Cada fase se mide sin sus primeros 10 s (transición); p50/p95 = mediana de los valores por segundo.

- **Punto de degradación:** F4 Estrés (primera fase con p95 > 1000 ms o errores > 5 %)
- **Recuperación OK:** SÍ — p95 F6 = 50 ms vs límite 1.2 × p95 F1 = 72 ms; errores F6 = 0.0 %
- **Tiempo hasta recuperar en F6:** 28 s (incluye la ventana de 10 s de Locust)
- **CP-02 validación bajo carga:** SÍ — 1448 inválidas enviadas: 1448 respondieron 422, 0 respondieron 500, 0 otro código, 0 sin respuesta (timeout o conexión rechazada)
- **CP-04 fallas técnicas:** 143 timeouts (> 5 s), 0 errores 5xx, 0 conexiones rechazadas/cortadas, 0 otras; la API siguió respondiendo en F6: SÍ

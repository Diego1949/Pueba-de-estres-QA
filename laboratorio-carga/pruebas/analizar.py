r"""Lee los CSV de Locust, calcula métricas por fase, aplica criterios y grafica.
Uso en Windows, después de la prueba (desde laboratorio-carga):  python pruebas\analizar.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # genera la imagen sin abrir ventanas
import matplotlib.pyplot as plt
import pandas as pd

RES = Path(__file__).resolve().parent.parent / "resultados"
# Deben coincidir con FasesDeCarga de locustfile.py: (nombre, duración en s)
FASES = [("F1 Normal", 30), ("F2 Carga", 30), ("F3 Alta", 30),
         ("F4 Estrés", 30), ("F5 Pico", 30), ("F6 Recuperación", 60)]
INICIOS = [sum(d for _, d in FASES[:i]) for i in range(len(FASES))]
# Cada fase se mide en su tramo estable: se descartan sus primeros 10 s porque
# (1) Locust da el p50/p95 de los ÚLTIMOS 10 s y aún mezcla la fase anterior y
# (2) subir o bajar usuarios tarda unos segundos (fallas de transición).
TRANSICION = 10
INVALIDO = "POST /api/pedidos [inválido]"


def leer(nombre):
    """Locust guarda los CSV con la codificación del sistema (cp1252 en Windows)."""
    try:
        return pd.read_csv(RES / nombre, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(RES / nombre, encoding="cp1252")


def contar(fallas, patron):
    """Suma las ocurrencias de los errores cuyo texto contiene el patrón."""
    return int(fallas[fallas["Error"].str.contains(patron, case=False)]["Occurrences"].sum())


# 1) Historial segundo a segundo (fila "Aggregated" = todas las peticiones)
h = leer("run_stats_history.csv").query("Name == 'Aggregated'").copy()
h["t"] = h["Timestamp"] - h["Timestamp"].min()       # segundos transcurridos
h[["p50", "p95"]] = h[["50%", "95%"]].apply(pd.to_numeric, errors="coerce")  # "N/A" -> vacío
h["peticiones"] = h["Total Request Count"].diff().fillna(h["Total Request Count"])
h["fallas"] = h["Total Failure Count"].diff().fillna(h["Total Failure Count"])
h["fase"] = [sum(t >= ini for ini in INICIOS) - 1 for t in h["t"]]  # nº de fase (0 = F1)

# 2) Métricas por fase (en su tramo estable)
filas = []
for i, (nombre, _) in enumerate(FASES):
    e = h[(h["fase"] == i) & (h["t"] >= INICIOS[i] + TRANSICION)]
    pet, fal = e["peticiones"].sum(), e["fallas"].sum()
    filas.append({"Fase": nombre, "Usuarios": int(e["User Count"].median()),
                  "Peticiones/s": round(pet / len(e), 1),
                  "p50 (ms)": round(e["p50"].median()), "p95 (ms)": round(e["p95"].median()),
                  "% errores": round(100 * fal / pet, 2) if pet else 0.0})
r = pd.DataFrame(filas)
ok = (r["p95 (ms)"] < 500) & (r["% errores"] < 1)
r["Estado"] = ok.map({True: "APROBADA", False: "NO APROBADA"})

# 3) Criterios: punto de degradación y recuperación
degradadas = r[(r["p95 (ms)"] > 1000) | (r["% errores"] > 5)]
punto = degradadas.index[0] if len(degradadas) else None
f1, f6 = r.iloc[0], r.iloc[-1]
umbral = 1.2 * f1["p95 (ms)"]
recupera = f6["p95 (ms)"] <= umbral and f6["% errores"] < 1
normales = h[(h["fase"] == len(FASES) - 1) & (h["p95"] <= umbral)]  # F6 ya bajo el umbral
t_rec = int(normales["t"].min() - INICIOS[-1]) if len(normales) else "nunca"

# 4) CP-02 (validación) y CP-04 (fallas técnicas) con los totales de Locust
stats, fallas = leer("run_stats.csv").set_index("Name"), leer("run_failures.csv")
fi = fallas[fallas["Name"] == INVALIDO]
inv_total, inv_falla = int(stats.loc[INVALIDO, "Request Count"]), contar(fi, "")
inv_otro, inv_500 = contar(fi, "llegó"), contar(fi, "llegó 500")  # códigos != 422
cp02 = inv_otro == 0  # toda respuesta recibida fue 422 (y por tanto ningún 500)
timeouts, e5xx = contar(fallas, "timed out"), contar(fallas, "Server Error|llegó 5")
rechazos = contar(fallas, "ConnectionRefused|ConnectionReset|ConnectionAborted|RemoteDisconn")
otras = contar(fallas, "") - timeouts - e5xx - rechazos
viva = f6["Peticiones/s"] > 0 and f6["% errores"] < 100

# 5) Archivos de salida: resumen.csv y resumen.md
r.to_csv(RES / "resumen.csv", index=False, encoding="utf-8-sig")
si = lambda v: "SÍ" if v else "NO"
md = ["# Resumen de la prueba de carga", "", "| " + " | ".join(r.columns) + " |",
      "|" + "---|" * len(r.columns)] + ["| " + " | ".join(map(str, f)) + " |" for f in r.values]
md += ["", "Criterio: fase APROBADA si p95 < 500 ms y errores < 1 %. Cada fase se mide sin "
       "sus primeros 10 s (transición); p50/p95 = mediana de los valores por segundo.", "",
       f"- **Punto de degradación:** {r.loc[punto, 'Fase'] if punto is not None else 'ninguno'}"
       " (primera fase con p95 > 1000 ms o errores > 5 %)",
       f"- **Recuperación OK:** {si(recupera)} — p95 F6 = {f6['p95 (ms)']} ms vs límite "
       f"1.2 × p95 F1 = {umbral:.0f} ms; errores F6 = {f6['% errores']} %",
       f"- **Tiempo hasta recuperar en F6:** {t_rec} s (incluye la ventana de 10 s de Locust)",
       f"- **CP-02 validación bajo carga:** {si(cp02)} — {inv_total} inválidas enviadas: "
       f"{inv_total - inv_falla} respondieron 422, {inv_500} respondieron 500, "
       f"{inv_otro - inv_500} otro código, {inv_falla - inv_otro} sin respuesta (timeout o "
       "conexión rechazada)",
       f"- **CP-04 fallas técnicas:** {timeouts} timeouts (> 5 s), {e5xx} errores 5xx, "
       f"{rechazos} conexiones rechazadas/cortadas, {otras} otras; "
       f"la API siguió respondiendo en F6: {si(viva)}"]
(RES / "resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))

# 6) Gráfica: 3 paneles con las fases sombreadas (rojo = fase NO APROBADA)
GRIS, AZUL, NARANJA, ROJO = "#898781", "#2a78d6", "#eb6834", "#d03b3b"
PANELES = [("Usuarios", [("User Count", AZUL, "Usuarios")]), ("p95 (ms)", [("p95", AZUL, "p95")]),
           ("Por segundo", [("Requests/s", AZUL, "Peticiones/s"),
                            ("Failures/s", NARANJA, "Errores/s")])]
fig, ejes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
ymax = h["User Count"].max() * 1.4
for ax, (titulo, series) in zip(ejes, PANELES):
    for i, (nombre, dur) in enumerate(FASES):
        aprobada = r.loc[i, "Estado"] == "APROBADA"
        ax.axvspan(INICIOS[i], INICIOS[i] + dur, lw=0, color="#f0efec" if aprobada else ROJO,
                   alpha=(0.9 if i % 2 else 0.0) if aprobada else 0.12)
        if ax is ejes[0]:  # nombre y estado de cada fase, arriba del primer panel
            ax.text(INICIOS[i] + dur / 2, ymax * 0.78, f"{nombre}\n{r.loc[i, 'Estado'].lower()}",
                    ha="center", fontsize=9, color="#0b0b0b" if aprobada else ROJO)
    if punto is not None:
        ax.axvline(INICIOS[punto], color=ROJO, ls="--", lw=1.2, label="Punto de degradación")
    for columna, color, nombre in series:
        ax.plot(h["t"], h[columna], color=color, lw=2, label=nombre)
    ax.set_ylabel(titulo)
    ax.grid(axis="y", color="#e1e0d9")
    ax.spines[["top", "right"]].set_visible(False)
ejes[0].set_ylim(0, ymax)
for lim, txt in [(500, "aprobado < 500 ms"), (1000, "degradación > 1000 ms")]:
    ejes[1].axhline(lim, color=GRIS, ls=":", lw=1)
    ejes[1].text(1, lim, txt, va="bottom", fontsize=8, color=GRIS)
ejes[2].legend(loc="upper left", frameon=False)
ejes[2].set_xlabel("Tiempo transcurrido (s)")
fig.suptitle("Prueba de carga por fases — API tienda ficticia (1 worker)")
fig.tight_layout()
fig.savefig(RES / "grafica.png", dpi=130)
print(f"\nArchivos generados en {RES}: resumen.csv, resumen.md, grafica.png")

"""Resume y grafica resultados de validacion cruzada del proyecto.

Ejecutar despues de consolidar los CSV de results/parciales/.
Las comparaciones son descriptivas: no reemplazan la revision de
cobertura de escenarios, folds ni la seleccion final del modelo.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


RAIZ = Path(__file__).resolve().parents[2]
RESULTADOS = RAIZ / "results"
COLUMNAS = {
    "modelo", "rasgo", "escenario_n", "ruido", "fold",
    "r_pearson", "rmse", "tiempo_s",
}


def resumir(datos):
    """Calcula medias y desviaciones por modelo y escenario.

    Args:
        datos (pd.DataFrame): una fila por fold de cada modelo.

    Returns:
        pd.DataFrame: resumen con promedios, desvios y folds.
    """
    faltantes = COLUMNAS - set(datos.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas: {sorted(faltantes)}")
    if datos.empty:
        raise ValueError("No hay resultados para comparar")

    datos = datos.copy()
    datos["escenario_n"] = pd.to_numeric(
        datos["escenario_n"], errors="raise"
    ).astype(int)
    for columna in ("fold", "r_pearson", "rmse", "tiempo_s"):
        datos[columna] = pd.to_numeric(datos[columna], errors="raise")
    if datos[list(COLUMNAS)].isna().any().any():
        raise ValueError("Los resultados contienen valores vacios")

    datos["escenario"] = datos.apply(
        lambda fila: (
            "holstein" if fila["rasgo"] != "fenotipo"
            else f"sim_n{fila['escenario_n']}"
        ),
        axis=1,
    )
    claves = ["escenario", "rasgo", "ruido", "modelo"]
    if datos.duplicated(claves + ["fold"]).any():
        raise ValueError("Hay folds duplicados en el consolidado")

    resumen = datos.groupby(claves, as_index=False).agg(
        n_folds=("fold", "nunique"),
        r_media=("r_pearson", "mean"),
        r_desv=("r_pearson", "std"),
        rmse_media=("rmse", "mean"),
        rmse_desv=("rmse", "std"),
        tiempo_medio_s=("tiempo_s", "mean"),
    )
    return resumen.sort_values(claves).reset_index(drop=True)


def graficar(resumen, carpeta):
    """Guarda un grafico de r y RMSE para cada escenario disponible.

    Args:
        resumen (pd.DataFrame): salida de resumir().
        carpeta (Path): directorio donde guardar las imagenes.

    Returns:
        list[Path]: rutas de los graficos generados.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for (escenario, rasgo, ruido), grupo in resumen.groupby(
        ["escenario", "rasgo", "ruido"], sort=True
    ):
        grupo = grupo.sort_values("r_media", ascending=True)
        fig, ejes = plt.subplots(1, 2, figsize=(11, 4))
        ejes[0].barh(grupo["modelo"], grupo["r_media"])
        ejes[0].set_xlabel("r de Pearson medio (mayor es mejor)")
        ejes[1].barh(grupo["modelo"], grupo["rmse_media"])
        ejes[1].set_xlabel("RMSE medio (menor es mejor)")
        fig.suptitle(f"{escenario} - {rasgo} - {ruido}")
        fig.tight_layout()
        destino = carpeta / f"e6_{escenario}_{rasgo}_{ruido}.png"
        fig.savefig(destino, dpi=150, bbox_inches="tight")
        plt.close(fig)
        rutas.append(destino)
    return rutas

def graficar_folds(datos, carpeta):
    """Compara Pearson y RMSE por fold entre modelos."""
    carpeta.mkdir(parents=True, exist_ok=True)

    datos = datos.copy()
    datos["escenario"] = datos.apply(
        lambda fila: (
            "holstein" if fila["rasgo"] != "fenotipo"
            else f"sim_n{int(fila['escenario_n'])}"
        ),
        axis=1,
    )

    rutas = []

    for (escenario, rasgo, ruido), grupo in datos.groupby(
        ["escenario", "rasgo", "ruido"]
    ):
        if grupo["modelo"].nunique() < 2:
            continue

        fig, ejes = plt.subplots(1, 2, figsize=(11, 4))

        for modelo, filas in grupo.groupby("modelo"):
            filas = filas.sort_values("fold")

            ejes[0].plot(
                filas["fold"],
                filas["r_pearson"],
                marker="o",
                label=modelo,
            )

            ejes[1].plot(
                filas["fold"],
                filas["rmse"],
                marker="o",
                label=modelo,
            )

        ejes[0].set_ylabel("Pearson r")
        ejes[1].set_ylabel("RMSE")

        for eje in ejes:
            eje.set_xlabel("Fold")
            eje.set_xticks(sorted(grupo["fold"].unique()))
            eje.legend()
            eje.grid(alpha=0.3)

        fig.suptitle(f"{escenario} - {rasgo} - {ruido}")
        fig.tight_layout()

        destino = carpeta / f"e6_folds_{escenario}_{rasgo}_{ruido}.png"
        fig.savefig(destino, dpi=150, bbox_inches="tight")
        plt.close(fig)

        rutas.append(destino)

    return rutas

def main():
    """Lee resultados.csv, guarda resumen y graficos comparativos."""
    entrada = RESULTADOS / "resultados.csv"
    if not entrada.exists():
        raise FileNotFoundError(
            "Falta results/resultados.csv: ejecuta --consolidar primero"
        )
    datos = pd.read_csv(entrada)
    resumen = resumir(datos)
    salida = RESULTADOS / "resumen_e6.csv"
    resumen.to_csv(salida, index=False, float_format="%.6f")
    graficos = graficar(resumen, RESULTADOS / "figures")
    graficos += graficar_folds(datos, RESULTADOS / "figures")
    
    print(resumen.round(3).to_string(index=False))
    print(f"\nResumen guardado: {salida.relative_to(RAIZ)}")
    print(f"Graficos creados: {len(graficos)}")
    incompletos = resumen[resumen["n_folds"] != 5]
    if not incompletos.empty:
        print("ADVERTENCIA: hay evaluaciones sin los 5 folds")
    print("Nota: un ganador final requiere resultados comparables completos.")


if __name__ == "__main__":
    main()

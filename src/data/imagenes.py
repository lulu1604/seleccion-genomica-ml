"""
imagenes.py

Que hace:
    Modulo de imagenes para el proyecto de Seleccion Genomica de Precision
    en Ganado Vacuno. Lee la tabla de medidas corporales (measurements.xlsx)
    del dataset "Cattle side view and back view dataset" (Bai, 2024,
    Mendeley Data, DOI 10.17632/h2s22wr5py.2), empareja cada fila con sus
    fotos de la carpeta "side view/" y "back view/", redimensiona las
    imagenes a 224x224 y genera results/imagenes_index.csv con el indice
    final.

    Estructura real del dataset (confirmada al abrir el ZIP):
        Cattle side and back view images/
            measurements.xlsx          -> columnas: Num, Oblique body
                                           length (cm), Withers height(cm),
                                           Heart girth(cm), Hip length (cm),
                                           Body weight (kg)
            side view/{Num}.png        -> vista lateral, un archivo por Num
            back view/{Num}.png        -> vista posterior (el animal 50
                                           viene como .jpg en vez de .png)

    Este modulo NO se cruza con los datos genomicos (Holstein/AlphaSimR).
    Es un modulo aparte: de la foto se estima peso y medidas corporales.

Como se corre:
    python src/data/imagenes.py \
        --tabla "data/raw/imagenes/Cattle side and back view images/measurements.xlsx" \
        --lateral "data/raw/imagenes/Cattle side and back view images/side view" \
        --posterior "data/raw/imagenes/Cattle side and back view images/back view" \
        --salida results/imagenes_index.csv \
        --procesadas data/processed/imagenes \
        --muestra data/sample/imagenes \
        --n-muestra 3

Que genera:
    - results/imagenes_index.csv: indice con id_animal_img, rutas de las
      fotos redimensionadas, y las medidas corporales.
    - data/processed/imagenes/: TODAS las fotos redimensionadas a 224x224
      (esta carpeta NO se sube al repo, la bloquea el .gitignore).
    - data/sample/imagenes/: N fotos de ejemplo ya redimensionadas
      (estas si se suben al repo).
    - Imprime en consola cuantos animales quedaron completos (lateral +
      posterior + medidas) y cuantos se perdieron, con el motivo.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from PIL import Image

TAMANO_SALIDA = (224, 224)
EXTENSIONES_POSIBLES = (".png", ".jpg", ".jpeg")

RENOMBRE_COLUMNAS = {
    "Num": "id_animal_img",
    "Oblique body length (cm)": "largo_oblicuo_cm",
    "Withers height(cm)": "altura_cruz_cm",
    "Heart girth(cm)": "perimetro_toracico_cm",
    "Hip length (cm)": "longitud_cadera_cm",
    "Body weight (kg)": "peso_kg",
}


def cargar_tabla(ruta_tabla: Path) -> pd.DataFrame:
    df = pd.read_excel(ruta_tabla)
    columnas_faltantes = set(RENOMBRE_COLUMNAS) - set(df.columns)
    if columnas_faltantes:
        raise ValueError(
            f"Faltan columnas esperadas en la tabla: {columnas_faltantes}. "
            f"Columnas encontradas: {list(df.columns)}"
        )
    df = df.rename(columns=RENOMBRE_COLUMNAS)
    df["id_animal_img"] = df["id_animal_img"].astype(int).astype(str)
    return df


def buscar_foto(carpeta: Path, id_animal: str) -> Path | None:
    """Busca {id_animal}.png / .jpg / .jpeg dentro de la carpeta."""
    for ext in EXTENSIONES_POSIBLES:
        candidato = carpeta / f"{id_animal}{ext}"
        if candidato.exists():
            return candidato
    return None


def redimensionar_y_guardar(ruta_origen: Path, ruta_destino: Path) -> bool:
    try:
        with Image.open(ruta_origen) as img:
            img = img.convert("RGB")
            img_redim = img.resize(TAMANO_SALIDA)
            ruta_destino.parent.mkdir(parents=True, exist_ok=True)
            img_redim.save(ruta_destino, quality=90)
        return True
    except Exception as e:
        print(f"  [ERROR] No se pudo abrir {ruta_origen}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tabla", required=True, type=Path,
                         help="Ruta a measurements.xlsx")
    parser.add_argument("--lateral", required=True, type=Path,
                         help="Carpeta 'side view' con las fotos originales")
    parser.add_argument("--posterior", required=True, type=Path,
                         help="Carpeta 'back view' con las fotos originales")
    parser.add_argument("--salida", default=Path("results/imagenes_index.csv"),
                         type=Path, help="Ruta del CSV de salida")
    parser.add_argument("--procesadas", default=Path("data/processed/imagenes"),
                         type=Path,
                         help="Carpeta donde se guardan TODAS las fotos redimensionadas (no se sube al repo)")
    parser.add_argument("--muestra", default=Path("data/sample/imagenes"),
                         type=Path,
                         help="Carpeta de ejemplo que si se sube al repo")
    parser.add_argument("--n-muestra", type=int, default=3,
                         help="Cuantos animales de ejemplo copiar a data/sample/")
    args = parser.parse_args()

    print(f"Leyendo tabla de medidas: {args.tabla}")
    df = cargar_tabla(args.tabla)
    print(f"  {len(df)} filas en la tabla")

    filas_salida = []
    completos, incompletos = 0, 0
    motivos_incompletos = []
    ids_muestra = []

    for _, fila in df.iterrows():
        id_animal = fila["id_animal_img"]
        foto_lat = buscar_foto(args.lateral, id_animal)
        foto_pos = buscar_foto(args.posterior, id_animal)

        if foto_lat is None or foto_pos is None:
            incompletos += 1
            faltantes = []
            if foto_lat is None:
                faltantes.append("foto lateral")
            if foto_pos is None:
                faltantes.append("foto posterior")
            motivos_incompletos.append(f"{id_animal}: falta {', '.join(faltantes)}")
            continue

        ruta_lat_dest = args.procesadas / f"{id_animal}_lat.jpg"
        ruta_pos_dest = args.procesadas / f"{id_animal}_pos.jpg"
        ok_lat = redimensionar_y_guardar(foto_lat, ruta_lat_dest)
        ok_pos = redimensionar_y_guardar(foto_pos, ruta_pos_dest)

        if not (ok_lat and ok_pos):
            incompletos += 1
            motivos_incompletos.append(f"{id_animal}: error al procesar imagen")
            continue

        filas_salida.append({
            "id_animal_img": id_animal,
            "ruta_lateral": str(ruta_lat_dest),
            "ruta_posterior": str(ruta_pos_dest),
            "peso_kg": fila["peso_kg"],
            "altura_cruz_cm": fila["altura_cruz_cm"],
            "perimetro_toracico_cm": fila["perimetro_toracico_cm"],
            "largo_oblicuo_cm": fila["largo_oblicuo_cm"],
            "longitud_cadera_cm": fila["longitud_cadera_cm"],
        })
        completos += 1

        if len(ids_muestra) < args.n_muestra:
            ids_muestra.append((id_animal, ruta_lat_dest, ruta_pos_dest))

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas_salida).to_csv(args.salida, index=False)

    args.muestra.mkdir(parents=True, exist_ok=True)
    for id_animal, ruta_lat, ruta_pos in ids_muestra:
        for origen in (ruta_lat, ruta_pos):
            if origen.exists():
                destino = args.muestra / origen.name
                destino.write_bytes(origen.read_bytes())

    print("\n--- Resumen ---")
    print(f"Animales completos (lateral + posterior + medidas): {completos}")
    print(f"Animales incompletos: {incompletos}")
    if motivos_incompletos:
        print("Detalle de incompletos:")
        for m in motivos_incompletos:
            print(f"  - {m}")
    print(f"\nIndice final guardado en: {args.salida}")
    print(f"Muestra de ejemplo ({len(ids_muestra)} animales) guardada en: {args.muestra}")


if __name__ == "__main__":
    sys.exit(main())

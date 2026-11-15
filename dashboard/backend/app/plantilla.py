"""Plantilla de Excel para subir animales: hojas Instrucciones, Animales y ADN.

Excel aguanta 16,384 columnas y el ADN tiene 42,551 marcadores, así que en la hoja
ADN los marcadores van en filas y cada animal en una columna. `leer_excel` lo
devuelve en el mismo formato ancho que el CSV (`id_animal, tipo, nombre, SNP1..`),
y el resto de la validación la hace `genomica.leer_genotipos`, igual que con el CSV.
"""
import io

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font
from openpyxl.worksheet.datavalidation import DataValidation

from .genomica import MAX_ANIMALES, ErrorGenotipos

TIPOS = ("Toro", "Vaca", "Vaquilla")
INSTRUCCIONES = [
    "Cómo usar esta plantilla",
    "1. Manda una muestra de cada animal (pelo de la cola o sangre) a un laboratorio de genotipado bovino.",
    "   Pide el chip de 50 mil marcadores (BovineSNP50) con resultados en formato 0, 1, 2.",
    '2. En la hoja "Animales", escribe una fila por animal: su código (id_animal), si es Toro, Vaca o Vaquilla,',
    "   y su nombre si quieres.",
    '3. En la hoja "ADN", pon en la fila 1 el mismo código de cada animal (una columna por animal)',
    "   y pega debajo los resultados del laboratorio, en el mismo orden de marcadores de la columna A.",
    '4. Guarda el archivo y súbelo en BOVIGEN con el botón "Subir archivo".',
    "5. Si algo falta, BOVIGEN te dirá qué corregir.",
    "Funciona solo con ganado Holstein.",
]


def _negrita(hoja, valores: list) -> list:
    celdas = []
    for v in valores:
        c = WriteOnlyCell(hoja, v)
        c.font = Font(bold=True)
        celdas.append(c)
    return celdas


def _libro(snps: list[str], animales: list[tuple[str, str, str]], adn: np.ndarray | None) -> bytes:
    """animales = [(id, tipo, nombre)]; adn = matriz (n_animales, n_snps) o None si está vacía."""
    wb = Workbook(write_only=True)

    hoja = wb.create_sheet("Instrucciones")
    hoja.column_dimensions["A"].width = 110
    hoja.append(_negrita(hoja, [INSTRUCCIONES[0]]))
    for linea in INSTRUCCIONES[1:]:
        hoja.append([linea])

    hoja = wb.create_sheet("Animales")
    hoja.freeze_panes = "A2"
    for col, ancho in zip("ABC", (16, 12, 24)):
        hoja.column_dimensions[col].width = ancho
    lista = DataValidation(type="list", formula1=f'"{",".join(TIPOS)}"', allow_blank=True,
                           showErrorMessage=True, error="Elige Toro, Vaca o Vaquilla.")
    lista.add(f"B2:B{MAX_ANIMALES + 1}")
    hoja.data_validations.append(lista)
    hoja.append(_negrita(hoja, ["id_animal", "tipo", "nombre"]))
    for fila in animales:
        hoja.append(list(fila))

    hoja = wb.create_sheet("ADN")
    hoja.freeze_panes = "B2"
    hoja.column_dimensions["A"].width = 14
    hoja.append(_negrita(hoja, ["marcador"] + [a[0] for a in animales]))
    for j, snp in enumerate(snps):
        hoja.append([snp] if adn is None else [snp, *adn[:, j].tolist()])

    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def crear_plantilla(snps: list[str]) -> bytes:
    """Plantilla vacía: Animales sin filas y ADN solo con la columna `marcador`."""
    return _libro(list(snps), [], None)


def crear_ejemplo_excel(df_ejemplo: pd.DataFrame, snps: list[str]) -> bytes:
    """La plantilla llena con los animales del CSV de ejemplo (tipo Toro, sin nombre)."""
    snps = list(snps)
    animales = [(str(i), "Toro", "") for i in df_ejemplo["id_animal"]]
    adn = df_ejemplo[snps].to_numpy(dtype=np.int8)
    return _libro(snps, animales, adn)


def _texto(valor) -> str:
    """Celda -> texto: 2042.0 -> '2042', None -> ''."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def _numero(valor) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return np.nan  # leer_genotipos lo rechaza como celda vacía o inválida


def _leer_animales(hoja) -> list[tuple[str, str, str]]:
    filas = hoja.iter_rows(values_only=True)
    encabezado = [_texto(v).lower() for v in next(filas, ())]
    if "id_animal" not in encabezado:
        raise ErrorGenotipos("La hoja Animales debe tener la columna id_animal en la fila 1.")
    col = {nombre: encabezado.index(nombre) for nombre in ("id_animal", "tipo", "nombre") if nombre in encabezado}

    def celda(fila, nombre):
        k = col.get(nombre)
        return _texto(fila[k]) if k is not None and k < len(fila) else ""

    animales = []
    for fila in filas:
        ident = celda(fila, "id_animal")
        if not ident:
            continue  # filas vacías
        tipo = celda(fila, "tipo")
        canonico = next((t for t in TIPOS if t.lower() == tipo.lower()), None)
        if tipo and canonico is None:
            raise ErrorGenotipos(f"El tipo de {ident} debe ser Toro, Vaca o Vaquilla (o dejarse vacío).")
        animales.append((ident, canonico or "", celda(fila, "nombre")))
    if not animales:
        raise ErrorGenotipos("La hoja Animales no tiene animales.")
    return animales


def _leer_adn(hoja, ids: list[str], snps: list[str]) -> tuple[list[str], np.ndarray]:
    """Devuelve (marcadores encontrados, matriz animales x marcadores) solo con los de `snps`."""
    filas = hoja.iter_rows(values_only=True)
    encabezado = [_texto(v) for v in next(filas, ())]
    columnas = {}
    for k, ident in enumerate(encabezado[1:], start=1):
        if not ident:
            continue
        if ident in columnas:
            raise ErrorGenotipos(f"La columna {ident} aparece dos veces en la hoja ADN.")
        columnas[ident] = k
    for ident in ids:
        if ident not in columnas:
            raise ErrorGenotipos(
                f"El animal {ident} está en la hoja Animales pero no tiene columna en la hoja ADN.")
    for ident in columnas:
        if ident not in ids:
            raise ErrorGenotipos(f"La columna {ident} de la hoja ADN no está en la hoja Animales.")

    pedidos = set(snps)
    posiciones = [columnas[i] for i in ids]
    leidos = {}
    for fila in filas:
        marcador = _texto(fila[0]) if fila else ""
        if marcador in pedidos:
            leidos[marcador] = [_numero(fila[k]) if k < len(fila) else np.nan for k in posiciones]
    presentes = [s for s in snps if s in leidos]
    matriz = np.array([leidos[s] for s in presentes], dtype=np.float32).reshape(len(presentes), len(ids))
    return presentes, matriz.T


def leer_excel(contenido: bytes, snps: list[str]) -> pd.DataFrame:
    """Lee las hojas Animales y ADN y devuelve `id_animal, tipo, nombre, SNP1..` (formato del CSV).

    Los marcadores que falten se dejan fuera para que `leer_genotipos` diga cuántos faltan.
    """
    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - cualquier archivo que no abre es "no es la plantilla"
        raise ErrorGenotipos("No se pudo abrir el Excel. Sube la plantilla de BOVIGEN (.xlsx).")
    try:
        if not {"Animales", "ADN"} <= set(libro.sheetnames):
            raise ErrorGenotipos("La plantilla debe tener las hojas Animales y ADN.")
        animales = _leer_animales(libro["Animales"])
        ids = [a[0] for a in animales]
        presentes, matriz = _leer_adn(libro["ADN"], ids, list(snps))
    finally:
        libro.close()
    df = pd.DataFrame(matriz, columns=presentes)
    df.insert(0, "nombre", [a[2] for a in animales])
    df.insert(0, "tipo", [a[1] for a in animales])
    df.insert(0, "id_animal", ids)
    return df

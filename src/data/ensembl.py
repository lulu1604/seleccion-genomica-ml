"""Ensembl SNP annotation for Bos taurus.

Que hace:
  - consulta la REST API de Ensembl para un SNP dado;
  - devuelve cromosoma, posición y gen más cercano;
  - guarda una caché local para no repetir llamadas;
  - exporta una tabla con las columnas esperadas por el proyecto.

Como se corre:
  python src/data/ensembl.py --snp-list SNP1 SNP2 SNP3 SNP4 SNP5 \
      --output results/snp_annot.csv

  python src/data/ensembl.py --input data/sample/holstein/snp_ids.csv \
      --output results/snp_annot.csv

Que genera:
  - results/snp_annot.csv: snp_id,cromosoma,posicion,gen
  - data/processed/ensembl_cache/: respuestas ya consultadas para reutilizar
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable
from urllib import parse, request, error

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "processed" / "ensembl_cache"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "snp_annot.csv"


def _normalize_snp_id(snp_id: str) -> str:
    return str(snp_id).strip()


def _cache_path_for(snp_id: str) -> Path:
    safe_id = parse.quote(_normalize_snp_id(snp_id), safe="")
    return CACHE_DIR / f"{safe_id}.json"


def _read_cache(snp_id: str) -> dict | None:
    path = _cache_path_for(snp_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except (TypeError, ValueError, OSError):
        pass
    return None


def _write_cache(snp_id: str, payload: dict) -> None:
    cache_path = _cache_path_for(snp_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _api_get(url: str, timeout: int = 20) -> dict:
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=timeout) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8"))


def _lookup_gene_symbol(gene_stable_id: str) -> str:
    if not gene_stable_id:
        return ""
    gene_id = parse.quote(gene_stable_id, safe="")
    url = f"https://rest.ensembl.org/lookup/id/{gene_id}?content-type=application/json"
    try:
        payload = _api_get(url)
        if isinstance(payload, dict):
            value = payload.get("display_name") or payload.get("name") or payload.get("id")
            if value:
                return str(value)
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                value = first.get("display_name") or first.get("name") or first.get("id")
                if value:
                    return str(value)
    except (ValueError, error.HTTPError, error.URLError, OSError):
        pass
    return ""


def fetch_snp_annotation(
    snp_id: str,
    use_cache: bool = True,
    timeout: int = 20,
    species: str = "bos_taurus",
) -> dict:
    """Return {snp_id, cromosoma, posicion, gen} for one SNP.

    Si la consulta falla porque el SNP no existe o porque la API está caida,
    la fila se devuelve con cromosoma/posición/gen vacíos y no rompe el flujo.
    """
    snp_id = _normalize_snp_id(snp_id)
    empty_row = {"snp_id": snp_id, "cromosoma": "", "posicion": "", "gen": ""}
    if not snp_id:
        return empty_row

    if use_cache:
        cached = _read_cache(snp_id)
        if cached is not None:
            return {
                "snp_id": cached.get("snp_id", snp_id),
                "cromosoma": str(cached.get("cromosoma", "")),
                "posicion": str(cached.get("posicion", "")),
                "gen": str(cached.get("gen", "")),
            }

    url = (
        "https://rest.ensembl.org/variation/"
        f"{parse.quote(species, safe='')}/{parse.quote(snp_id, safe='')}"
        "?content-type=application/json"
    )

    try:
        payload = _api_get(url, timeout=timeout)
    except (ValueError, error.HTTPError, error.URLError, OSError):
        row = empty_row.copy()
        if use_cache:
            _write_cache(snp_id, row)
        return row

    mappings = payload.get("mappings") if isinstance(payload, dict) else []
    mapping = mappings[0] if isinstance(mappings, list) and mappings else {}
    if not isinstance(mapping, dict):
        mapping = {}

    cromosoma = str(mapping.get("seq_region_name") or payload.get("seq_region_name") or "")
    posicion = mapping.get("start") or payload.get("start") or ""
    gene_stable_id = (
        mapping.get("gene_stable_id")
        or mapping.get("gene_id")
        or (mapping.get("gene") if isinstance(mapping.get("gene"), str) else "")
        or ""
    )

    gen = _lookup_gene_symbol(gene_stable_id) if gene_stable_id else ""
    row = {
        "snp_id": snp_id,
        "cromosoma": cromosoma,
        "posicion": str(posicion),
        "gen": str(gen),
    }

    if use_cache:
        _write_cache(snp_id, row)
    return row


def annotate_snps(
    snp_ids: Iterable[str],
    output_path: str | Path = DEFAULT_OUTPUT,
    use_cache: bool = True,
    timeout: int = 20,
) -> pd.DataFrame:
    """Annotate multiple SNPs and save them as a CSV with the expected schema."""
    ids = [ _normalize_snp_id(snp_id) for snp_id in snp_ids ]
    ids = [snp_id for snp_id in ids if snp_id]
    if not ids:
        raise ValueError("No SNP ids were provided for annotation.")

    rows = [fetch_snp_annotation(item, use_cache=use_cache, timeout=timeout) for item in ids]
    df = pd.DataFrame(rows, columns=["snp_id", "cromosoma", "posicion", "gen"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df


def _read_ids_from_file(path: str | Path) -> list[str]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if "snp_id" not in df.columns:
        raise ValueError(f"The file {csv_path} must contain a 'snp_id' column.")
    return df["snp_id"].astype(str).tolist()


def main() -> int:
    global CACHE_DIR

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snp-list", nargs="*", default=[], help="Lista de SNPs a consultar")
    parser.add_argument("--input", type=Path, default=None, help="CSV con columna snp_id")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Ruta del CSV de salida")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="Carpeta de caché")
    parser.add_argument("--no-cache", action="store_true", help="Desactiva la caché local")
    parser.add_argument("--timeout", type=int, default=20, help="Timeout de cada consulta")
    args = parser.parse_args()

    CACHE_DIR = args.cache_dir

    if args.input is not None:
        ids = _read_ids_from_file(args.input)
    elif args.snp_list:
        ids = args.snp_list
    else:
        ids = ["SNP1", "SNP2", "SNP3", "SNP4", "SNP5"]

    df = annotate_snps(ids, output_path=args.output, use_cache=not args.no_cache, timeout=args.timeout)
    print(df.to_string(index=False))
    print(f"\nArchivo guardado en: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

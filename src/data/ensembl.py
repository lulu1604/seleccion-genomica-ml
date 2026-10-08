"""Ensembl SNP annotation for Bos taurus.

Que hace:
  - consulta la REST API de Ensembl para un SNP dado;
  - devuelve cromosoma, posición y gen más cercano;
  - guarda una caché local para no repetir llamadas;
  - exporta una tabla con las columnas esperadas por el proyecto.

Como se corre:
  python src/data/ensembl.py --snp-list rs109421300 NOEXISTE12345 \
      --output results/snp_annot.csv

  python src/data/ensembl.py --input path/to/snp_ids.csv \
      --output results/snp_annot.csv

Que genera:
  - results/snp_annot.csv: snp_id,cromosoma,posicion,gen
  - data/processed/ensembl_cache/: respuestas ya consultadas para reutilizar
"""

from __future__ import annotations

import argparse
import json
import time
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


def _api_get(url: str, timeout: int = 20, max_retries: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
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
        except (ValueError, error.HTTPError, error.URLError, OSError, TimeoutError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"No response received for {url!r}.")


def _normalize_gene_symbol(gene_symbol: str | None) -> str:
    if gene_symbol is None:
        return ""
    return str(gene_symbol).strip().upper()


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
                return _normalize_gene_symbol(value)
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                value = first.get("display_name") or first.get("name") or first.get("id")
                if value:
                    return _normalize_gene_symbol(value)
    except (ValueError, error.HTTPError, error.URLError, OSError):
        pass
    return ""


def _extract_vep_gene_symbol(payload: object) -> str:
    """Return the gene symbol from a VEP payload, preferring the overlapping gene over nearby genes."""
    if not isinstance(payload, list):
        return ""

    preferred: list[str] = []
    fallback: list[str] = []
    for variant in payload:
        if not isinstance(variant, dict):
            continue
        for consequence in variant.get("transcript_consequences") or []:
            if not isinstance(consequence, dict):
                continue
            symbol = _normalize_gene_symbol(
                consequence.get("gene_symbol") or consequence.get("gene_name") or consequence.get("symbol")
            )
            if not symbol:
                continue
            distance = consequence.get("distance")
            if distance is None or distance == "" or distance == 0:
                preferred.append(symbol)
            else:
                fallback.append(symbol)
        if not preferred:
            symbol = _normalize_gene_symbol(
                variant.get("gene_symbol") or variant.get("gene_name") or variant.get("symbol")
            )
            if symbol:
                preferred.append(symbol)
    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]
    return ""


def _should_cache_missing_variant(exc: Exception) -> bool:
    return isinstance(exc, error.HTTPError) and exc.code in {400, 404}


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
    except (ValueError, error.HTTPError, error.URLError, OSError, TimeoutError) as exc:
        row = empty_row.copy()
        if use_cache and _should_cache_missing_variant(exc):
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

    gen = ""
    vep_url = (
        "https://rest.ensembl.org/vep/"
        f"{parse.quote(species, safe='')}/id/{parse.quote(snp_id, safe='')}"
        "?content-type=application/json"
    )
    try:
        vep_payload = _api_get(vep_url, timeout=timeout)
        gen = _extract_vep_gene_symbol(vep_payload)
    except (ValueError, error.HTTPError, error.URLError, OSError, TimeoutError):
        gen = ""

    if not gen and gene_stable_id:
        gen = _lookup_gene_symbol(gene_stable_id)

    row = {
        "snp_id": snp_id,
        "cromosoma": cromosoma,
        "posicion": str(posicion),
        "gen": str(gen),
    }

    if not cromosoma and not posicion and not gen and use_cache:
        _write_cache(snp_id, row)
    elif use_cache:
        _write_cache(snp_id, row)
    return row


def annotate_snps(
    snp_ids: Iterable[str],
    output_path: str | Path = DEFAULT_OUTPUT,
    use_cache: bool = True,
    timeout: int = 20,
) -> pd.DataFrame:
    """Annotate multiple SNPs and save them as a CSV with the expected schema."""
    ids = [_normalize_snp_id(snp_id) for snp_id in snp_ids]
    ids = [snp_id for snp_id in ids if snp_id]
    if not ids:
        raise ValueError("No SNP ids were provided for annotation.")

    rows = []
    for index, item in enumerate(ids):
        if index > 0:
            time.sleep(0.1)
        rows.append(fetch_snp_annotation(item, use_cache=use_cache, timeout=timeout))
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
        ids = ["rs109421300"]

    df = annotate_snps(ids, output_path=args.output, use_cache=not args.no_cache, timeout=args.timeout)
    print(df.to_string(index=False))
    print(f"\nArchivo guardado en: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

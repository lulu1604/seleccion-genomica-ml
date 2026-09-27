"""
preprocess_holstein.py — Preprocesamiento del dataset Holstein 2015

Convierte los archivos raw (File S1 genotipos, File S2 targets) del estudio
Zhang et al. (2015) en archivos procesados listos para modelado.

Uso:
    python src/data/preprocess_holstein.py

Requisitos:
    - data/raw/holstein_2015/016261_files1.zip  (File S1: genotipos)
    - data/raw/holstein_2015/016261_files2.txt   (File S2: targets/EBV)

Genera:
    - data/processed/holstein/X.parquet   (id_animal + SNP1..SNP42551)
    - data/processed/holstein/y.csv
    - data/processed/holstein/animal_ids.csv
    - data/processed/holstein/qc_report.json
    - data/processed/holstein/manifest.json
"""
import json
import hashlib
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Paths (relative to project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "holstein_2015"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "holstein"

ZIP_PATH = RAW_DIR / "016261_files1.zip"
GENO_ENTRY = "cattle_genotypes.txt"
TARGETS_PATH = RAW_DIR / "016261_files2.txt"

# Expected constants (validated, not assumed)
EXPECTED_ANIMALS = 5024
EXPECTED_SNPS = 42551
VALID_GENO_VALUES = {0, 1, 2}


def md5_file(path: Path) -> str:
    """Compute MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_identifiers(identifiers: list[str]) -> str:
    """Return a stable checksum for an ordered identifier sequence."""
    payload = "\n".join(identifiers).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_raw_files():
    """Check that required raw files exist."""
    missing = []
    if not ZIP_PATH.exists():
        missing.append(str(ZIP_PATH))
    if not TARGETS_PATH.exists():
        missing.append(str(TARGETS_PATH))
    if missing:
        raise FileNotFoundError(
            f"Missing raw files: {missing}\n"
            f"Download them following docs/fuente_datos.md and place in {RAW_DIR}"
        )
    print(f"[OK] Raw files located in {RAW_DIR}")


def read_genotypes() -> tuple[pd.DataFrame, list[str], list[str]]:
    """
    Read genotypes from ZIP, return (DataFrame, animal_ids, snp_ids).

    Reads the full matrix once as uint8. The dataset is small enough for this
    stage, but no transformation, imputation, or feature filtering is applied.
    The genotypes file is tab-separated with:
      - First column: 'Animal' (ID)
      - Remaining columns: 'SNP1' .. 'SNP42551' (values 0, 1, 2)
    """
    print("[...] Reading genotypes from ZIP (this may take ~30-60s)...")
    t0 = time.time()

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        if GENO_ENTRY not in z.namelist():
            raise ValueError(
                f"Expected '{GENO_ENTRY}' inside {ZIP_PATH.name}, found {z.namelist()}"
            )
        with z.open(GENO_ENTRY) as f:
            header_line = f.readline().decode("utf-8").strip()
            columns = header_line.split("\t")

    id_col = columns[0]
    snp_cols = columns[1:]
    expected_snp_cols = [f"SNP{i}" for i in range(1, EXPECTED_SNPS + 1)]
    if id_col != "Animal":
        raise ValueError(f"Expected genotype ID column 'Animal', got '{id_col}'")
    if snp_cols != expected_snp_cols:
        raise ValueError("Genotype SNP column schema does not match SNP1..SNP42551")

    # Read using pandas from zip — pandas can read from zip directly
    # Use dtype=uint8 for SNPs to minimize RAM
    dtypes = {col: np.uint8 for col in snp_cols}
    dtypes[id_col] = str

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        with z.open(GENO_ENTRY) as f:
            df = pd.read_csv(f, sep="\t", dtype=dtypes)

    if list(df.columns) != columns:
        raise ValueError("Genotype columns changed while reading the ZIP entry")

    animal_ids = list(df[id_col])
    df = df.drop(columns=[id_col])

    elapsed = time.time() - t0
    print(f"[OK] Genotypes loaded: {df.shape} in {elapsed:.1f}s")
    mem_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
    print(f"     RAM usage: {mem_mb:.1f} MB (uint8)")

    return df, animal_ids, snp_cols


def validate_genotypes(df: pd.DataFrame, animal_ids: list[str], snp_ids: list[str]) -> dict:
    """Validate genotype matrix. Returns QC metrics dict."""
    print("[...] Validating genotypes...")

    n_animals, n_snps = df.shape
    qc = {}

    # Shape
    qc["n_animales_raw"] = n_animals
    qc["n_snps_raw"] = n_snps

    if n_animals != EXPECTED_ANIMALS:
        raise ValueError(f"Expected {EXPECTED_ANIMALS} animals, got {n_animals}")
    if n_snps != EXPECTED_SNPS:
        raise ValueError(f"Expected {EXPECTED_SNPS} SNPs, got {n_snps}")

    # Duplicated animal IDs
    dup_ids = len(animal_ids) - len(set(animal_ids))
    qc["duplicated_animals_x"] = dup_ids
    if dup_ids > 0:
        raise ValueError(f"Found {dup_ids} duplicated animal IDs in genotypes")

    # Duplicated SNP columns
    dup_snps = len(snp_ids) - len(set(snp_ids))
    qc["duplicated_snp_names"] = dup_snps
    if dup_snps > 0:
        raise ValueError(f"Found {dup_snps} duplicated SNP column names")

    # Unique genotype values
    unique_vals = set()
    for col in df.columns:
        unique_vals.update(df[col].unique().tolist())
    qc["genotype_values_found"] = sorted(unique_vals)

    unexpected = unique_vals - VALID_GENO_VALUES
    if unexpected:
        raise ValueError(f"Unexpected genotype values found: {unexpected}")

    # Missing values
    total_missing = int(df.isnull().sum().sum())
    qc["missing_genotypes"] = total_missing
    if total_missing > 0:
        raise ValueError(f"Found {total_missing} missing genotype values")

    print(f"[OK] Genotypes validated: {n_animals} animals × {n_snps} SNPs, values={{0,1,2}}, 0 missing")
    return qc


def read_targets() -> pd.DataFrame:
    """Read targets file (File S2)."""
    print("[...] Reading targets...")
    df = pd.read_csv(TARGETS_PATH, sep="\t")
    # Rename 'id' -> 'id_animal' for project convention
    df = df.rename(columns={"id": "id_animal"})
    print(f"[OK] Targets loaded: {df.shape}, columns={list(df.columns)}")
    return df


def validate_targets(df: pd.DataFrame) -> dict:
    """Validate targets DataFrame. Returns QC metrics dict."""
    print("[...] Validating targets...")
    qc = {}

    expected_cols = {"id_animal", "mkg", "fpro", "scs"}
    actual_cols = set(df.columns)
    if actual_cols != expected_cols:
        raise ValueError(f"Expected columns {expected_cols}, got {actual_cols}")

    qc["n_animales_y"] = len(df)
    qc["duplicated_animals_y"] = int(df["id_animal"].duplicated().sum())
    if qc["duplicated_animals_y"] > 0:
        raise ValueError(f"Found {qc['duplicated_animals_y']} duplicated IDs in targets")

    # Missing per column
    missing = df.isnull().sum().to_dict()
    qc["missing_targets"] = missing
    total_missing = sum(missing.values())
    if total_missing > 0:
        raise ValueError(f"Targets contain missing values: {missing}")

    if (df["id_animal"].astype(str).str.strip() == "").any():
        raise ValueError("Targets contain blank animal IDs")
    for col in ["mkg", "fpro", "scs"]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Target '{col}' must be numeric, got {df[col].dtype}")

    # Stats
    qc["target_stats"] = {}
    for col in ["mkg", "fpro", "scs"]:
        qc["target_stats"][col] = {
            "mean": round(float(df[col].mean()), 6),
            "std": round(float(df[col].std()), 6),
            "min": round(float(df[col].min()), 6),
            "max": round(float(df[col].max()), 6),
        }

    print(f"[OK] Targets validated: {len(df)} animals, 0 missing, 3 traits")
    return qc


def align_ids(
    X: pd.DataFrame,
    y: pd.DataFrame,
    x_ids: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Align X and y by animal ID. Returns aligned (X, y, ids)."""
    print("[...] Aligning IDs...")

    set_x = set(x_ids)
    set_y = set(y["id_animal"])
    common = sorted(set_x & set_y)
    only_x = set_x - set_y
    only_y = set_y - set_x

    print(f"     IDs in X: {len(set_x)}, in y: {len(set_y)}, common: {len(common)}")
    if only_x or only_y:
        sample_x = sorted(only_x)[:5]
        sample_y = sorted(only_y)[:5]
        raise ValueError(
            "ID mismatch between genotypes and targets: "
            f"only_in_X={len(only_x)} {sample_x}; only_in_y={len(only_y)} {sample_y}"
        )

    # Build index for X rows
    x_id_to_idx = {aid: i for i, aid in enumerate(x_ids)}

    # Sort common IDs to ensure deterministic order
    common_indices_x = [x_id_to_idx[aid] for aid in common]
    X_aligned = X.iloc[common_indices_x].reset_index(drop=True)

    y_indexed = y.set_index("id_animal")
    y_aligned = y_indexed.loc[common].reset_index()

    if X_aligned.shape[0] != y_aligned.shape[0]:
        raise RuntimeError("Shape mismatch after ID alignment")
    if list(y_aligned["id_animal"]) != common:
        raise RuntimeError("Targets are not in the expected aligned ID order")

    print(f"[OK] Aligned: {X_aligned.shape[0]} animals in deterministic order")
    return X_aligned, y_aligned, common


def save_processed(
    X: pd.DataFrame,
    y: pd.DataFrame,
    animal_ids: list[str],
    snp_ids: list[str],
) -> dict:
    """
    Save processed data to data/processed/holstein/.

    Format decision: Parquet for X.
    ---
    Rationale:
    - Parquet with 42,551 columns is technically viable and was requested by the team.
    - pyarrow handles wide tables efficiently with columnar storage.
    - Parquet preserves column names (SNP IDs) natively — no separate metadata file needed.
    - Compression (snappy) reduces size from ~200 MB to ~65 MB.
    - uint8 dtype is preserved through Arrow's uint8 type.
    - Read speed is excellent: ~2-3s for full matrix.
    - Alternatives considered:
        * NPY: Faster I/O but loses column names; requires separate snp_ids.csv.
        * NPZ: Same as NPY + compression, but no pandas integration.
        * Feather: Similar to Parquet but less compression for this data shape.
    - Decision: Parquet wins on balance of metadata preservation, compression,
      and team familiarity. The loader abstracts the format anyway.
    """
    print("[...] Saving processed data...")
    t0 = time.time()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if list(y["id_animal"]) != animal_ids:
        raise ValueError("Refusing to save: y IDs do not match the supplied X row order")
    if len(animal_ids) != X.shape[0]:
        raise ValueError("Refusing to save: number of animal IDs does not match X rows")

    # --- X.parquet ---
    # First column is id_animal (string) so each row carries its own key;
    # animal_ids.csv is kept as a backup of the same order.
    x_path = PROCESSED_DIR / "X.parquet"

    # Convert to pyarrow Table: id_animal (string) + uint8 SNP columns
    fields = [pa.field("id_animal", pa.string())]
    fields += [pa.field(name, pa.uint8()) for name in snp_ids]
    schema = pa.schema(fields)
    columns = {"id_animal": [str(aid) for aid in animal_ids]}
    columns.update({name: X[name].values for name in snp_ids})
    table = pa.table(columns, schema=schema)
    pq.write_table(table, x_path, compression="snappy")
    x_size = x_path.stat().st_size

    # --- y.csv ---
    y_path = PROCESSED_DIR / "y.csv"
    y.to_csv(y_path, index=False)
    y_size = y_path.stat().st_size

    # --- animal_ids.csv ---
    # Backup row key: must always equal X.parquet id_animal and y.id_animal.
    animal_ids_path = PROCESSED_DIR / "animal_ids.csv"
    pd.DataFrame({"id_animal": animal_ids}).to_csv(animal_ids_path, index=False)
    animal_ids_size = animal_ids_path.stat().st_size

    elapsed = time.time() - t0
    print(f"[OK] Saved in {elapsed:.1f}s")
    print(f"     X.parquet: {x_size:,} bytes ({x_size/1024/1024:.1f} MB)")
    print(f"     y.csv:     {y_size:,} bytes ({y_size/1024:.1f} KB)")

    return {
        "x_path": str(x_path.relative_to(PROJECT_ROOT)),
        "y_path": str(y_path.relative_to(PROJECT_ROOT)),
        "animal_ids_path": str(animal_ids_path.relative_to(PROJECT_ROOT)),
        "x_size_bytes": x_size,
        "y_size_bytes": y_size,
        "animal_ids_size_bytes": animal_ids_size,
        "animal_ids_sha256": sha256_identifiers(animal_ids),
        "snp_ids_sha256": sha256_identifiers(snp_ids),
        "formato_final_elegido": "parquet (snappy compression, uint8)",
        "save_time_s": round(elapsed, 1),
    }


def generate_qc_report(qc_geno: dict, qc_targets: dict, save_info: dict, total_time: float):
    """Generate machine-readable QC report."""
    report = {
        "dataset": "Holstein 2015 (Zhang et al.)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_time_s": round(total_time, 1),
        # Raw dimensions
        "n_animales_raw": qc_geno["n_animales_raw"],
        "n_snps_raw": qc_geno["n_snps_raw"],
        # Final dimensions (after alignment)
        "n_animales_final": save_info.get("n_animales_final", qc_geno["n_animales_raw"]),
        "n_snps_final": qc_geno["n_snps_raw"],
        "shape_x": [save_info.get("n_animales_final", qc_geno["n_animales_raw"]), qc_geno["n_snps_raw"]],
        "shape_y": [save_info.get("n_animales_final", qc_geno["n_animales_raw"]), 4],
        # Validation
        "genotype_values_found": qc_geno["genotype_values_found"],
        "missing_genotypes": qc_geno["missing_genotypes"],
        "missing_targets": qc_targets["missing_targets"],
        "duplicated_animals_x": qc_geno["duplicated_animals_x"],
        "duplicated_animals_y": qc_targets["duplicated_animals_y"],
        "duplicated_snp_names": qc_geno["duplicated_snp_names"],
        # ID comparison
        "ids_x": qc_geno["n_animales_raw"],
        "ids_y": qc_targets["n_animales_y"],
        "ids_common": save_info.get("n_animales_final", qc_geno["n_animales_raw"]),
        "ids_only_x": 0,
        "ids_only_y": 0,
        # Targets
        "targets": ["mkg", "fpro", "scs"],
        "target_stats": qc_targets["target_stats"],
        # Data types
        "dtypes": {
            "X": "uint8",
            "y_id_animal": "string",
            "y_mkg": "float64",
            "y_fpro": "float64",
            "y_scs": "float64",
        },
        # Files
        "file_sizes": {
            "raw_zip": ZIP_PATH.stat().st_size,
            "raw_targets": TARGETS_PATH.stat().st_size,
            "processed_x": save_info["x_size_bytes"],
            "processed_y": save_info["y_size_bytes"],
            "processed_animal_ids": save_info["animal_ids_size_bytes"],
        },
        "formato_final_elegido": save_info["formato_final_elegido"],
        "memoria_aproximada_x_mb": round(
            save_info.get("n_animales_final", qc_geno["n_animales_raw"])
            * qc_geno["n_snps_raw"]
            / 1024
            / 1024,
            1,
        ),
        # Checksums for traceability
        "checksums_raw": {
            "016261_files1.zip_md5": md5_file(ZIP_PATH),
            "016261_files2.txt_md5": md5_file(TARGETS_PATH),
        },
        "checksums_processed_contract": {
            "animal_ids_sha256": save_info["animal_ids_sha256"],
            "snp_ids_sha256": save_info["snp_ids_sha256"],
        },
    }

    qc_path = PROCESSED_DIR / "qc_report.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[OK] QC report saved: {qc_path.relative_to(PROJECT_ROOT)}")
    return report


def generate_manifest(qc_report: dict, save_info: dict):
    """Generate reproducibility manifest."""
    manifest = {
        "dataset_name": "Holstein 2015",
        "version": "1.1",
        "source": "Zhang et al. (2015), G3: Genes, Genomes, Genetics",
        "doi": "https://doi.org/10.1534/g3.114.016261",
        "raw_files": [
            "data/raw/holstein_2015/016261_files1.zip",
            "data/raw/holstein_2015/016261_files2.txt",
        ],
        "processed_files": [
            save_info["x_path"],
            save_info["y_path"],
            save_info["animal_ids_path"],
        ],
        "n_animales": qc_report["n_animales_final"],
        "n_snps": qc_report["n_snps_final"],
        "targets": ["mkg", "fpro", "scs"],
        "formato": save_info["formato_final_elegido"],
        "dtype_x": "uint8",
        "script": "src/data/preprocess_holstein.py",
        "generated_at": qc_report["timestamp"],
        "checksums_raw": qc_report["checksums_raw"],
        "animal_ids_sha256": save_info["animal_ids_sha256"],
        "snp_ids_sha256": save_info["snp_ids_sha256"],
    }

    manifest_path = PROCESSED_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest saved: {manifest_path.relative_to(PROJECT_ROOT)}")


def main():
    print("=" * 60)
    print("PREPROCESSING: Holstein 2015 Dataset")
    print("=" * 60)
    t_start = time.time()

    # Step 1: Validate raw files exist
    validate_raw_files()

    # Step 2: Read genotypes
    X, animal_ids_x, snp_ids = read_genotypes()

    # Step 3: Validate genotypes
    qc_geno = validate_genotypes(X, animal_ids_x, snp_ids)

    # Step 4: Read targets
    y = read_targets()

    # Step 5: Validate targets
    qc_targets = validate_targets(y)

    # Step 6: Align by ID
    X, y, common_ids = align_ids(X, y, animal_ids_x)

    # Step 7: Save processed
    save_info = save_processed(X, y, common_ids, snp_ids)
    save_info["n_animales_final"] = len(common_ids)

    # Step 8: QC report
    total_time = time.time() - t_start
    qc_report = generate_qc_report(qc_geno, qc_targets, save_info, total_time)

    # Step 9: Manifest
    generate_manifest(qc_report, save_info)

    # Summary
    total_time = time.time() - t_start
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Animals:      {len(common_ids)}")
    print(f"  SNPs:         {len(snp_ids)}")
    print(f"  X shape:      {X.shape}")
    print(f"  y shape:      {y.shape}")
    print(f"  X dtype:      uint8")
    print(f"  Format:       Parquet (snappy)")
    print(f"  X file size:  {save_info['x_size_bytes']/1024/1024:.1f} MB")
    print(f"  y file size:  {save_info['y_size_bytes']/1024:.1f} KB")
    print(f"  RAM for X:    {qc_report['memoria_aproximada_x_mb']:.1f} MB")
    print(f"  Total time:   {total_time:.1f}s")
    print(f"  Output dir:   {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")
    print()
    print("[DONE] Holstein dataset ready for modeling.")


if __name__ == "__main__":
    main()

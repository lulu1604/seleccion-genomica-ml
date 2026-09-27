"""Safe loading interface for the processed Holstein 2015 dataset.

The genotype Parquet intentionally contains SNP columns only. Its row order is
bound to ``animal_ids.csv``; the loader validates that file against ``y.csv``
and the manifest before returning any data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "holstein"

X_PATH = PROCESSED_DIR / "X.parquet"
Y_PATH = PROCESSED_DIR / "y.csv"
ANIMAL_IDS_PATH = PROCESSED_DIR / "animal_ids.csv"
QC_PATH = PROCESSED_DIR / "qc_report.json"
MANIFEST_PATH = PROCESSED_DIR / "manifest.json"

EXPECTED_ANIMALS = 5024
EXPECTED_SNPS = 42551
VALID_TARGETS = ("mkg", "fpro", "scs")


def _sha256_identifiers(identifiers: list[str]) -> str:
    return hashlib.sha256("\n".join(identifiers).encode("utf-8")).hexdigest()


def _check_processed_exist() -> None:
    """Verify every artifact required by the persisted alignment contract."""
    required = (X_PATH, Y_PATH, ANIMAL_IDS_PATH, QC_PATH, MANIFEST_PATH)
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Processed Holstein artifacts not found: {missing}\n"
            "Run the preprocessing script first:\n"
            "  python src/data/preprocess_holstein.py\n"
            "Make sure the raw files are in data/raw/holstein_2015/"
        )


def _read_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_loaded_data(
    X_df: pd.DataFrame, y_df: pd.DataFrame, ids_df: pd.DataFrame, manifest: dict
) -> list[str]:
    """Validate schema, values, and the persisted X/y row-order contract."""
    expected_snp_ids = [f"SNP{i}" for i in range(1, EXPECTED_SNPS + 1)]
    expected_y_columns = ["id_animal", *VALID_TARGETS]

    if X_df.shape != (EXPECTED_ANIMALS, EXPECTED_SNPS):
        raise RuntimeError(
            f"Unexpected X shape {X_df.shape}; expected {(EXPECTED_ANIMALS, EXPECTED_SNPS)}"
        )
    if list(X_df.columns) != expected_snp_ids:
        raise RuntimeError("SNP column schema mismatch in X.parquet")
    if not all(dtype == np.dtype("uint8") for dtype in X_df.dtypes):
        raise RuntimeError("X.parquet must contain uint8 SNP columns")
    values = X_df.to_numpy(copy=False)
    if values.min() < 0 or values.max() > 2:
        raise RuntimeError("X.parquet contains genotype values outside {0, 1, 2}")

    if y_df.shape != (EXPECTED_ANIMALS, len(expected_y_columns)):
        raise RuntimeError(
            f"Unexpected y shape {y_df.shape}; expected {(EXPECTED_ANIMALS, len(expected_y_columns))}"
        )
    if list(y_df.columns) != expected_y_columns:
        raise RuntimeError(f"Unexpected y.csv columns {list(y_df.columns)}")
    if y_df.isna().to_numpy().any():
        raise RuntimeError("y.csv contains missing values")
    if y_df["id_animal"].duplicated().any() or (y_df["id_animal"].astype(str).str.strip() == "").any():
        raise RuntimeError("y.csv contains duplicate or blank animal IDs")
    if not all(pd.api.types.is_numeric_dtype(y_df[target]) for target in VALID_TARGETS):
        raise RuntimeError("y.csv target columns must be numeric")

    if list(ids_df.columns) != ["id_animal"] or len(ids_df) != EXPECTED_ANIMALS:
        raise RuntimeError("animal_ids.csv must contain exactly one id_animal column")
    if ids_df.isna().to_numpy().any() or ids_df["id_animal"].duplicated().any():
        raise RuntimeError("animal_ids.csv contains missing or duplicate IDs")

    animal_ids = ids_df["id_animal"].astype(str).tolist()
    if y_df["id_animal"].astype(str).tolist() != animal_ids:
        raise RuntimeError("Animal IDs in y.csv do not match animal_ids.csv row order")

    if manifest.get("animal_ids_sha256") != _sha256_identifiers(animal_ids):
        raise RuntimeError("animal_ids.csv checksum does not match manifest.json")
    if manifest.get("snp_ids_sha256") != _sha256_identifiers(expected_snp_ids):
        raise RuntimeError("X.parquet SNP schema checksum does not match manifest.json")

    return animal_ids


def _load_validated() -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict]:
    _check_processed_exist()
    X_df = pd.read_parquet(X_PATH)
    y_df = pd.read_csv(Y_PATH)
    ids_df = pd.read_csv(ANIMAL_IDS_PATH)
    manifest = _read_manifest()
    animal_ids = _validate_loaded_data(X_df, y_df, ids_df, manifest)
    return X_df, y_df, animal_ids, manifest


def load_holstein(target: Optional[str] = None, as_numpy: bool = True) -> tuple:
    """Load validated Holstein genotypes and either all or one target.

    ``X[i]`` and ``y[i]`` always refer to the same ``id_animal`` because the
    loader validates the persisted row-key file and manifest before returning.
    """
    if target is not None and target not in VALID_TARGETS:
        raise ValueError(f"Invalid target '{target}'. Must be one of {VALID_TARGETS}")

    X_df, y_df, _, _ = _load_validated()
    X = X_df.to_numpy(dtype=np.uint8, copy=False) if as_numpy else X_df
    y = y_df[target].to_numpy() if target is not None else y_df
    return X, y


def load_holstein_meta() -> dict:
    """Load validated metadata, animal IDs, and SNP IDs."""
    X_df, _, animal_ids, manifest = _load_validated()
    with open(QC_PATH, "r", encoding="utf-8") as handle:
        qc_report = json.load(handle)
    return {
        "qc_report": qc_report,
        "manifest": manifest,
        "animal_ids": animal_ids,
        "snp_ids": list(X_df.columns),
    }


if __name__ == "__main__":
    X, y = load_holstein()
    print(f"X shape: {X.shape}, dtype: {X.dtype}")
    print(f"y shape: {y.shape}, columns: {list(y.columns)}")

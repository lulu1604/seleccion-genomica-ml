"""Regression tests for the persisted Holstein X/y alignment contract."""
from __future__ import annotations

import hashlib
import importlib
import json

import pandas as pd
import pytest


loader = importlib.import_module("src.data.load_holstein")
preprocess = importlib.import_module("src.data.preprocess_holstein")


def _sha256_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _configure_loader_paths(monkeypatch: pytest.MonkeyPatch, processed_dir):
    monkeypatch.setattr(loader, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(loader, "X_PATH", processed_dir / "X.parquet")
    monkeypatch.setattr(loader, "Y_PATH", processed_dir / "y.csv")
    monkeypatch.setattr(loader, "ANIMAL_IDS_PATH", processed_dir / "animal_ids.csv", raising=False)
    monkeypatch.setattr(loader, "QC_PATH", processed_dir / "qc_report.json")
    monkeypatch.setattr(loader, "MANIFEST_PATH", processed_dir / "manifest.json")
    monkeypatch.setattr(loader, "EXPECTED_ANIMALS", 2, raising=False)
    monkeypatch.setattr(loader, "EXPECTED_SNPS", 2, raising=False)


def _write_processed_fixture(processed_dir, *, animal_ids, y_ids=None, snp_columns=None):
    processed_dir.mkdir()
    y_ids = y_ids or animal_ids
    snp_columns = snp_columns or ["SNP1", "SNP2"]
    pd.DataFrame({column: [0, 1] for column in snp_columns}, dtype="uint8").to_parquet(
        processed_dir / "X.parquet", index=False
    )
    pd.DataFrame(
        {
            "id_animal": y_ids,
            "mkg": [0.1, 0.2],
            "fpro": [0.3, 0.4],
            "scs": [0.5, 0.6],
        }
    ).to_csv(processed_dir / "y.csv", index=False)
    pd.DataFrame({"id_animal": animal_ids}).to_csv(
        processed_dir / "animal_ids.csv", index=False
    )
    (processed_dir / "qc_report.json").write_text("{}", encoding="utf-8")
    (processed_dir / "manifest.json").write_text(
        json.dumps(
            {
                "animal_ids_sha256": _sha256_ids(animal_ids),
                "snp_ids_sha256": _sha256_ids(snp_columns),
            }
        ),
        encoding="utf-8",
    )


def test_loader_rejects_reordered_animal_ids(monkeypatch, tmp_path):
    """Changing the persisted row order must prevent silently misaligned X/y."""
    processed_dir = tmp_path / "processed"
    _configure_loader_paths(monkeypatch, processed_dir)
    _write_processed_fixture(processed_dir, animal_ids=["Anim2", "Anim1"], y_ids=["Anim1", "Anim2"])

    with pytest.raises(RuntimeError, match="Animal IDs in y.csv do not match animal_ids.csv"):
        loader.load_holstein()


def test_loader_rejects_unexpected_snp_schema(monkeypatch, tmp_path):
    """A malformed Parquet schema must not be accepted merely because row counts match."""
    processed_dir = tmp_path / "processed"
    _configure_loader_paths(monkeypatch, processed_dir)
    _write_processed_fixture(processed_dir, animal_ids=["Anim1", "Anim2"], snp_columns=["SNP1", "SNP3"])

    with pytest.raises(RuntimeError, match="SNP column schema mismatch"):
        loader.load_holstein()


def test_loader_rejects_animal_id_file_with_wrong_manifest_checksum(monkeypatch, tmp_path):
    """A changed row-key file must be detected even when y currently matches it."""
    processed_dir = tmp_path / "processed"
    _configure_loader_paths(monkeypatch, processed_dir)
    _write_processed_fixture(processed_dir, animal_ids=["Anim1", "Anim2"])
    (processed_dir / "manifest.json").write_text(
        json.dumps({"animal_ids_sha256": "wrong", "snp_ids_sha256": _sha256_ids(["SNP1", "SNP2"])}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="animal_ids.csv checksum"):
        loader.load_holstein()


def test_align_ids_rejects_any_animal_present_in_only_one_source():
    """A source-population discrepancy must fail instead of dropping an animal."""
    X = pd.DataFrame({"SNP1": [0, 1]})
    y = pd.DataFrame(
        {
            "id_animal": ["Anim1", "Anim3"],
            "mkg": [0.1, 0.2],
            "fpro": [0.3, 0.4],
            "scs": [0.5, 0.6],
        }
    )

    with pytest.raises(ValueError, match="ID mismatch"):
        preprocess.align_ids(X, y, ["Anim1", "Anim2"])


def test_validate_targets_rejects_missing_target_value():
    """A missing EBV must stop preprocessing rather than be written downstream."""
    y = pd.DataFrame(
        {
            "id_animal": ["Anim1", "Anim2"],
            "mkg": [0.1, None],
            "fpro": [0.3, 0.4],
            "scs": [0.5, 0.6],
        }
    )

    with pytest.raises(ValueError, match="missing values"):
        preprocess.validate_targets(y)


def test_save_processed_persists_the_x_row_key(monkeypatch, tmp_path):
    """The processed X row order must be materialized outside Parquet metadata."""
    monkeypatch.setattr(preprocess, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(preprocess, "PROCESSED_DIR", tmp_path / "data" / "processed" / "holstein")
    X = pd.DataFrame({"SNP1": [0, 1], "SNP2": [2, 0]}, dtype="uint8")
    y = pd.DataFrame(
        {
            "id_animal": ["Anim1", "Anim2"],
            "mkg": [0.1, 0.2],
            "fpro": [0.3, 0.4],
            "scs": [0.5, 0.6],
        }
    )

    save_info = preprocess.save_processed(X, y, ["Anim1", "Anim2"], ["SNP1", "SNP2"])

    stored_ids = pd.read_csv(preprocess.PROCESSED_DIR / "animal_ids.csv")
    assert stored_ids["id_animal"].tolist() == ["Anim1", "Anim2"]
    assert save_info["animal_ids_sha256"] == _sha256_ids(["Anim1", "Anim2"])

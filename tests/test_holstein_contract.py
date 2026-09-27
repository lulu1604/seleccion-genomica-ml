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


def _animal_number(animal_id: str) -> int:
    return int(animal_id.removeprefix("Anim"))


def _write_processed_fixture(processed_dir, *, animal_ids, y_ids=None, x_ids=None, snp_columns=None):
    """Write a tiny processed dataset whose genotypes and targets encode each animal.

    Row for ``AnimN`` has every SNP equal to ``N - 1`` and ``mkg == N / 10``, so
    any misalignment between X, y and ids is visible in the values.
    """
    processed_dir.mkdir()
    y_ids = y_ids or animal_ids
    x_ids = x_ids or animal_ids
    snp_columns = snp_columns or ["SNP1", "SNP2"]
    X = pd.DataFrame({"id_animal": x_ids})
    for column in snp_columns:
        X[column] = pd.array([_animal_number(a) - 1 for a in x_ids], dtype="uint8")
    X.to_parquet(processed_dir / "X.parquet", index=False)
    pd.DataFrame(
        {
            "id_animal": y_ids,
            "mkg": [_animal_number(a) / 10 for a in y_ids],
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


def test_loader_rejects_x_rows_permuted_against_animal_ids(monkeypatch, tmp_path):
    """X.parquet rows reordered (with their ids) must not pass as aligned with y."""
    processed_dir = tmp_path / "processed"
    _configure_loader_paths(monkeypatch, processed_dir)
    _write_processed_fixture(processed_dir, animal_ids=["Anim1", "Anim2"], x_ids=["Anim2", "Anim1"])

    with pytest.raises(RuntimeError, match="id_animal in X.parquet does not match animal_ids.csv"):
        loader.load_holstein()


def test_cargar_returns_ids_aligned_with_x_rows(monkeypatch, tmp_path):
    """cargar() must return ids in the same order as the rows of X and y."""
    processed_dir = tmp_path / "processed"
    _configure_loader_paths(monkeypatch, processed_dir)
    _write_processed_fixture(processed_dir, animal_ids=["Anim2", "Anim1"])

    X, y, ids = loader.cargar("mkg")

    assert ids == ["Anim2", "Anim1"]
    assert X.shape == (2, 2)  # SNP columns only, no id_animal
    for i, animal_id in enumerate(ids):
        n = _animal_number(animal_id)
        assert X[i].tolist() == [n - 1, n - 1]
        assert y[i] == pytest.approx(n / 10)

    X_all, y_all, ids_all = loader.cargar()
    assert y_all["id_animal"].tolist() == ids_all == ids


def test_align_ids_keeps_x_and_y_rows_matched_when_y_order_differs():
    """Happy path: y in a different order than X must end row-by-row aligned."""
    x_ids = ["Anim1", "Anim2", "Anim10", "Anim3"]
    # SNP1 encodes the animal number so each X row is identifiable
    X = pd.DataFrame({"SNP1": [1, 2, 10, 3]}, dtype="uint8")
    y = pd.DataFrame(
        {
            "id_animal": ["Anim3", "Anim10", "Anim1", "Anim2"],
            "mkg": [3.0, 10.0, 1.0, 2.0],
            "fpro": [0.3, 1.0, 0.1, 0.2],
            "scs": [0.0, 0.0, 0.0, 0.0],
        }
    )

    X_aligned, y_aligned, ids = preprocess.align_ids(X, y, x_ids)

    assert len(ids) == len(X_aligned) == len(y_aligned) == 4
    assert y_aligned["id_animal"].tolist() == ids
    for i, animal_id in enumerate(ids):
        n = _animal_number(animal_id)
        assert X_aligned["SNP1"].iloc[i] == n
        assert y_aligned["mkg"].iloc[i] == pytest.approx(n)


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

    stored_x = pd.read_parquet(preprocess.PROCESSED_DIR / "X.parquet")
    assert list(stored_x.columns) == ["id_animal", "SNP1", "SNP2"]
    assert stored_x["id_animal"].tolist() == ["Anim1", "Anim2"]
    assert stored_x["SNP1"].tolist() == [0, 1]

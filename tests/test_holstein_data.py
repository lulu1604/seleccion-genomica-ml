"""
test_holstein_data.py — Tests ligeros para datos Holstein

Ejecuta sobre data/sample/holstein/ (NO requiere los 428 MB de datos raw).

Uso:
    python -m pytest tests/test_holstein_data.py -v
"""
import pandas as pd
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample" / "holstein"

EXPECTED_ANIMALS = 10
EXPECTED_SNPS = 20
VALID_GENO_VALUES = {0, 1, 2}
EXPECTED_TARGETS = ["mkg", "fpro", "scs"]


@pytest.fixture
def x_toy():
    return pd.read_csv(SAMPLE_DIR / "X_toy.csv")


@pytest.fixture
def y_toy():
    return pd.read_csv(SAMPLE_DIR / "y_toy.csv")


class TestSampleFiles:
    """Verify that the toy sample files exist and are well-formed."""

    def test_sample_dir_exists(self):
        assert SAMPLE_DIR.exists(), f"{SAMPLE_DIR} does not exist"

    def test_x_toy_exists(self):
        assert (SAMPLE_DIR / "X_toy.csv").exists()

    def test_y_toy_exists(self):
        assert (SAMPLE_DIR / "y_toy.csv").exists()


class TestXToy:
    """Validate X_toy.csv structure and content."""

    def test_shape(self, x_toy):
        # id_animal + 20 SNPs = 21 columns
        assert x_toy.shape == (EXPECTED_ANIMALS, EXPECTED_SNPS + 1)

    def test_has_id_column(self, x_toy):
        assert "id_animal" in x_toy.columns

    def test_n_snp_columns(self, x_toy):
        snp_cols = [c for c in x_toy.columns if c != "id_animal"]
        assert len(snp_cols) == EXPECTED_SNPS

    def test_unique_ids(self, x_toy):
        assert x_toy["id_animal"].nunique() == EXPECTED_ANIMALS

    def test_no_missing(self, x_toy):
        assert x_toy.isnull().sum().sum() == 0

    def test_genotype_values_only_012(self, x_toy):
        snp_cols = [c for c in x_toy.columns if c != "id_animal"]
        for col in snp_cols:
            values = set(x_toy[col].unique())
            assert values.issubset(VALID_GENO_VALUES), (
                f"Column {col} has invalid values: {values - VALID_GENO_VALUES}"
            )


class TestYToy:
    """Validate y_toy.csv structure and content."""

    def test_shape(self, y_toy):
        # id_animal + 3 targets = 4 columns
        assert y_toy.shape == (EXPECTED_ANIMALS, len(EXPECTED_TARGETS) + 1)

    def test_has_id_column(self, y_toy):
        assert "id_animal" in y_toy.columns

    def test_expected_target_columns(self, y_toy):
        for t in EXPECTED_TARGETS:
            assert t in y_toy.columns, f"Missing target column: {t}"

    def test_unique_ids(self, y_toy):
        assert y_toy["id_animal"].nunique() == EXPECTED_ANIMALS

    def test_no_missing(self, y_toy):
        assert y_toy.isnull().sum().sum() == 0

    def test_targets_are_float(self, y_toy):
        for t in EXPECTED_TARGETS:
            assert y_toy[t].dtype in ("float64", "float32"), (
                f"Target {t} should be float, got {y_toy[t].dtype}"
            )


class TestAlignment:
    """Verify X_toy and y_toy have the same animals in the same order."""

    def test_same_animal_count(self, x_toy, y_toy):
        assert x_toy.shape[0] == y_toy.shape[0]

    def test_same_ids(self, x_toy, y_toy):
        assert set(x_toy["id_animal"]) == set(y_toy["id_animal"])

    def test_same_order(self, x_toy, y_toy):
        assert list(x_toy["id_animal"]) == list(y_toy["id_animal"])

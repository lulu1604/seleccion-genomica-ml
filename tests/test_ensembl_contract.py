"""Contract tests for the Ensembl SNP annotation module."""

from __future__ import annotations

import urllib.error

from src.data.ensembl import annotate_snps, fetch_snp_annotation


def test_fetch_snp_annotation_uses_cache(monkeypatch, tmp_path):
    """The module stores successful answers and reuses them on a second call."""
    cache_dir = tmp_path / "cache"
    calls = {"count": 0}

    def fake_api_get(url: str, timeout: int = 20, **kwargs):
        calls["count"] += 1
        return {
            "mappings": [
                {
                    "seq_region_name": "14",
                    "start": 1802265,
                    "gene_stable_id": "ENSBTAG00000000001",
                }
            ]
        }

    def fake_lookup_gene_symbol(gene_stable_id: str):
        return "DGAT1"

    monkeypatch.setattr("src.data.ensembl.CACHE_DIR", cache_dir)
    monkeypatch.setattr("src.data.ensembl._api_get", fake_api_get)
    monkeypatch.setattr("src.data.ensembl._lookup_gene_symbol", fake_lookup_gene_symbol)

    first = fetch_snp_annotation("SNP1", use_cache=True)
    second = fetch_snp_annotation("SNP1", use_cache=True)

    assert first["snp_id"] == "SNP1"
    assert first["gen"] == "DGAT1"
    assert second == first
    assert calls["count"] == 1


def test_fetch_snp_annotation_handles_missing_snp(monkeypatch):
    """Unknown SNP IDs should not crash the pipeline; they must yield empty values."""

    def fake_api_get(url: str, timeout: int = 20, **kwargs):
        raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr("src.data.ensembl._api_get", fake_api_get)
    result = fetch_snp_annotation("SNP404", use_cache=False)

    assert result == {
        "snp_id": "SNP404",
        "cromosoma": "",
        "posicion": "",
        "gen": "",
    }


def test_annotate_snps_writes_expected_columns(monkeypatch, tmp_path):
    """The exported CSV keeps the original SNP ids and the fixed four-column schema."""

    def fake_api_get(url: str, timeout: int = 20, **kwargs):
        return {
            "mappings": [
                {"seq_region_name": "1", "start": 123, "gene_stable_id": "ENSBTAG00000000001"}
            ]
        }

    monkeypatch.setattr("src.data.ensembl._api_get", fake_api_get)
    monkeypatch.setattr("src.data.ensembl._lookup_gene_symbol", lambda gene_stable_id: "GAPDH")

    output_path = tmp_path / "snp_annot.csv"
    df = annotate_snps(["SNP1", "SNP2"], output_path=output_path, use_cache=False)

    assert list(df.columns) == ["snp_id", "cromosoma", "posicion", "gen"]
    assert list(df["snp_id"]) == ["SNP1", "SNP2"]
    assert output_path.exists()

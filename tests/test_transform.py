"""
Unit tests for the transform_bq_rows_to_experiment_input helper in main.py.

These tests are self-contained: no BigQuery, no Airtable, no FOE imports needed.
"""
import pytest

from main import transform_bq_rows_to_experiment_input


# ---------------------------------------------------------------------------
# Happy-path cases
# ---------------------------------------------------------------------------

def test_two_variant_transform():
    """Two BigQuery rows produce correct visitors / conversions / labels lists."""
    rows = [
        {"experience_variant_label": "Control", "visitors": 1000, "with_transaction": 100},
        {"experience_variant_label": "Variant_B", "visitors": 1050, "with_transaction": 130},
    ]
    result = transform_bq_rows_to_experiment_input("EXP_001", rows)

    assert result["experiment_id"] == "EXP_001"
    assert result["labels"] == ["Control", "Variant_B"]
    assert result["visitors"] == [1000, 1050]
    assert result["conversions"] == [100, 130]


def test_three_variant_transform():
    """Three variants are mapped in order."""
    rows = [
        {"experience_variant_label": "Control", "visitors": 2000, "with_transaction": 200},
        {"experience_variant_label": "B", "visitors": 1990, "with_transaction": 210},
        {"experience_variant_label": "C", "visitors": 2010, "with_transaction": 300},
    ]
    result = transform_bq_rows_to_experiment_input("EXP_002", rows)

    assert result["labels"] == ["Control", "B", "C"]
    assert result["visitors"] == [2000, 1990, 2010]
    assert result["conversions"] == [200, 210, 300]


def test_integer_coercion():
    """Numeric fields returned as floats by BigQuery are cast to int."""
    rows = [
        {"experience_variant_label": "A", "visitors": 500.0, "with_transaction": 50.0},
        {"experience_variant_label": "B", "visitors": 499.0, "with_transaction": 60.0},
    ]
    result = transform_bq_rows_to_experiment_input("EXP_003", rows)

    assert all(isinstance(v, int) for v in result["visitors"])
    assert all(isinstance(c, int) for c in result["conversions"])


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_empty_rows_raises_value_error():
    """An empty BQ result must raise ValueError rather than silently return bad data."""
    with pytest.raises(ValueError, match="No BigQuery rows"):
        transform_bq_rows_to_experiment_input("EXP_EMPTY", [])

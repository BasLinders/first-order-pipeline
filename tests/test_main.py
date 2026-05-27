"""
Integration-level tests for the main() orchestrator.

All external I/O (BigQuery, Airtable, FOE engines) is mocked so the test
suite has no runtime dependencies beyond the standard library and pytest.
"""
import os
from unittest.mock import MagicMock, patch, call

import pytest

import main as pipeline_main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BQ_ROWS = [
    {"experience_variant_label": "Control", "visitors": 1000, "with_transaction": 100},
    {"experience_variant_label": "Challenger", "visitors": 1000, "with_transaction": 130},
]

ENV_VARS = {
    "EXPERIMENT_ID": "EXP_INT",
    "START_DATE": "2024-01-01",
    "END_DATE": "2024-01-31",
    "VARIANTS": "Control,Challenger",
    "BQ_DATASET_PATH": "project.dataset",
    "QUERY_TYPE": "aggregated",
}


# ---------------------------------------------------------------------------
# main() happy path
# ---------------------------------------------------------------------------

@patch.dict(os.environ, ENV_VARS)
@patch("main.push_to_airtable")
@patch("main.run_bayesian_pipeline", return_value=[{"experiment_id": "EXP_INT", "engine": "bayesian", "results": []}])
@patch("main.run_frequentist_pipeline", return_value=[{"experiment_id": "EXP_INT", "engine": "frequentist", "results": []}])
@patch("main.fetch_bigquery_data", return_value=BQ_ROWS)
def test_main_happy_path(mock_bq, mock_freq, mock_bayes, mock_airtable):
    """main() calls BQ, both engines, and Airtable once each."""
    pipeline_main.main()

    mock_bq.assert_called_once_with(
        experiment_id="EXP_INT",
        start_date="2024-01-01",
        end_date="2024-01-31",
        variants=["Control", "Challenger"],
        dataset_path="project.dataset",
        query_type="aggregated",
    )
    mock_freq.assert_called_once()
    mock_bayes.assert_called_once()
    mock_airtable.assert_called_once()


@patch.dict(os.environ, ENV_VARS)
@patch("main.push_to_airtable")
@patch("main.run_bayesian_pipeline", return_value=[])
@patch("main.run_frequentist_pipeline", return_value=[{"experiment_id": "EXP_INT", "engine": "frequentist", "results": []}])
@patch("main.fetch_bigquery_data", return_value=BQ_ROWS)
def test_main_pushes_combined_payload(mock_bq, mock_freq, mock_bayes, mock_airtable):
    """Frequentist and Bayesian results are combined into one Airtable payload."""
    pipeline_main.main()

    payload = mock_airtable.call_args[0][0]
    assert isinstance(payload, list)
    # Only the frequentist result is non-empty here.
    assert any(r["engine"] == "frequentist" for r in payload)


# ---------------------------------------------------------------------------
# main() missing env vars
# ---------------------------------------------------------------------------

def test_main_raises_on_missing_env_vars():
    """main() raises EnvironmentError when required env vars are absent."""
    clean_env = {k: "" for k in ENV_VARS}
    with patch.dict(os.environ, clean_env, clear=False):
        # Also remove the keys so os.getenv returns None.
        for key in ENV_VARS:
            os.environ.pop(key, None)
        with pytest.raises(EnvironmentError, match="Missing required environment variables"):
            pipeline_main.main()


# ---------------------------------------------------------------------------
# main() BQ failure propagates
# ---------------------------------------------------------------------------

@patch.dict(os.environ, ENV_VARS)
@patch("main.fetch_bigquery_data", side_effect=RuntimeError("BQ unavailable"))
def test_main_propagates_bq_error(mock_bq):
    """An unrecoverable BigQuery error bubbles up from main()."""
    with pytest.raises(RuntimeError, match="BQ unavailable"):
        pipeline_main.main()

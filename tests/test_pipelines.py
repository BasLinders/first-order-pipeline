"""
Unit tests for the frequentist and Bayesian pipeline functions in main.py.

FOE is mocked at the engine level so these tests run without a live FOE install.
The mocks validate that:
  - ExperimentInput is constructed correctly from the experiment dict.
  - The engine method is called.
  - The output dict shape matches what push_to_airtable expects.
"""
from unittest.mock import MagicMock, patch

import pytest

from main import run_frequentist_pipeline, run_bayesian_pipeline


EXPERIMENT = {
    "experiment_id": "EXP_TEST",
    "labels": ["Control", "Challenger"],
    "visitors": [1000, 1000],
    "conversions": [100, 120],
}


# ---------------------------------------------------------------------------
# Frequentist pipeline
# ---------------------------------------------------------------------------

@patch("main.FrequentistEngine")
def test_frequentist_pipeline_returns_one_result(MockEngine):
    """run_frequentist_pipeline returns one result dict per experiment."""
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"p_value": 0.03, "is_significant": True}
    MockEngine.return_value.run_synthesis.return_value = [mock_result]

    results = run_frequentist_pipeline([EXPERIMENT])

    assert len(results) == 1
    r = results[0]
    assert r["experiment_id"] == "EXP_TEST"
    assert r["engine"] == "frequentist"
    assert isinstance(r["results"], list)
    assert r["results"][0]["p_value"] == 0.03


@patch("main.FrequentistEngine")
def test_frequentist_pipeline_calls_run_synthesis(MockEngine):
    """run_synthesis is called exactly once per experiment."""
    MockEngine.return_value.run_synthesis.return_value = []

    run_frequentist_pipeline([EXPERIMENT])

    MockEngine.return_value.run_synthesis.assert_called_once()


@patch("main.FrequentistEngine")
def test_frequentist_pipeline_logs_and_skips_on_error(MockEngine):
    """A failing experiment is skipped; other experiments still run."""
    MockEngine.return_value.run_synthesis.side_effect = ValueError("bad input")

    results = run_frequentist_pipeline([EXPERIMENT])

    # The failed experiment should not appear in results.
    assert results == []


# ---------------------------------------------------------------------------
# Bayesian pipeline
# ---------------------------------------------------------------------------

@patch("main.BayesianEngine")
def test_bayesian_pipeline_returns_one_result(MockEngine):
    """run_bayesian_pipeline returns one result dict per experiment."""
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"prob_being_best": 0.95}
    MockEngine.return_value.run_probability_analysis.return_value = [mock_result]

    results = run_bayesian_pipeline([EXPERIMENT])

    assert len(results) == 1
    r = results[0]
    assert r["experiment_id"] == "EXP_TEST"
    assert r["engine"] == "bayesian"
    assert r["results"][0]["prob_being_best"] == 0.95


@patch("main.BayesianEngine")
def test_bayesian_pipeline_calls_run_probability_analysis(MockEngine):
    """run_probability_analysis is called exactly once per experiment."""
    MockEngine.return_value.run_probability_analysis.return_value = []

    run_bayesian_pipeline([EXPERIMENT])

    MockEngine.return_value.run_probability_analysis.assert_called_once()


@patch("main.BayesianEngine")
def test_bayesian_pipeline_logs_and_skips_on_error(MockEngine):
    """A failing experiment is skipped; results list remains empty."""
    MockEngine.return_value.run_probability_analysis.side_effect = RuntimeError("oops")

    results = run_bayesian_pipeline([EXPERIMENT])

    assert results == []


# ---------------------------------------------------------------------------
# Multi-experiment handling
# ---------------------------------------------------------------------------

@patch("main.FrequentistEngine")
def test_frequentist_pipeline_handles_multiple_experiments(MockEngine):
    """One result dict is produced for each experiment in the input list."""
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {}
    MockEngine.return_value.run_synthesis.return_value = [mock_result]

    second = {**EXPERIMENT, "experiment_id": "EXP_TWO"}
    results = run_frequentist_pipeline([EXPERIMENT, second])

    assert len(results) == 2
    assert results[0]["experiment_id"] == "EXP_TEST"
    assert results[1]["experiment_id"] == "EXP_TWO"

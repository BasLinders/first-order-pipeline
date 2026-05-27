import logging
import os
from typing import List, Dict, Any

# 1. Import operational engines
from foe.frequentist.operations import FrequentistEngine
from foe.bayesian.operations import BayesianEngine
from foe.core.models import ExperimentInput
from src.extract import fetch_bigquery_data
from src.load import push_to_airtable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================================
# DATA TRANSFORMATION
# ==========================================

def transform_bq_rows_to_experiment_input(
    experiment_id: str,
    rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Converts a list of per-variant BigQuery rows (one row per variant)
    into an ExperimentInput-compatible dict.

    Expected BQ row keys: experience_variant_label, visitors, with_transaction.
    """
    if not rows:
        raise ValueError(f"No BigQuery rows returned for experiment {experiment_id}.")

    labels = [str(row["experience_variant_label"]) for row in rows]
    visitors = [int(row["visitors"]) for row in rows]
    conversions = [int(row["with_transaction"]) for row in rows]

    return {
        "experiment_id": experiment_id,
        "labels": labels,
        "visitors": visitors,
        "conversions": conversions,
    }


# ==========================================
# OPERATIONAL PIPELINES
# ==========================================

def run_frequentist_pipeline(experiments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("Starting Frequentist Pipeline...")
    engine = FrequentistEngine()
    results = []

    for exp in experiments:
        try:
            input_data = ExperimentInput(
                visitors=exp["visitors"],
                conversions=exp["conversions"],
                labels=exp.get("labels"),
            )
            stat_results = engine.run_synthesis(data=input_data)
            results.append({
                "experiment_id": exp["experiment_id"],
                "engine": "frequentist",
                "results": [r.model_dump() for r in stat_results],
            })
        except Exception as e:
            logger.error(f"Frequentist Engine failed on {exp.get('experiment_id')}: {e}")

    return results


def run_bayesian_pipeline(experiments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("Starting Bayesian Pipeline...")
    engine = BayesianEngine()
    results = []

    for exp in experiments:
        try:
            input_data = ExperimentInput(
                visitors=exp["visitors"],
                conversions=exp["conversions"],
                labels=exp.get("labels"),
            )
            prob_results = engine.run_probability_analysis(data=input_data)
            results.append({
                "experiment_id": exp["experiment_id"],
                "engine": "bayesian",
                "results": [r.model_dump() for r in prob_results],
            })
        except Exception as e:
            logger.error(f"Bayesian Engine failed on {exp.get('experiment_id')}: {e}")

    return results


# ==========================================
# PLACEHOLDER PIPELINES
# ==========================================

def run_behavioral_pipeline(experiments): raise NotImplementedError("BehavioralEngine not yet deployed.")
def run_continuous_pipeline(experiments): raise NotImplementedError("ContinuousMetricEngine not yet deployed.")
def run_interaction_pipeline(experiments): raise NotImplementedError("InteractionEngine not yet deployed.")
def run_pretest_pipeline(experiments): raise NotImplementedError("PretestEngine not yet deployed.")
def run_sequential_pipeline(experiments): raise NotImplementedError("SequentialEngine not yet deployed.")
def run_srm_pipeline(experiments): raise NotImplementedError("SRMEngine not yet deployed.")
def run_viz_pipeline(experiments): raise NotImplementedError("VizEngine not yet deployed.")


# ==========================================
# MAIN ORCHESTRATOR
# ==========================================

def main():
    # --- Configuration from environment variables ---
    experiment_id = os.getenv("EXPERIMENT_ID")
    start_date = os.getenv("START_DATE")
    end_date = os.getenv("END_DATE")
    raw_variants = os.getenv("VARIANTS", "")
    variants = [v.strip() for v in raw_variants.split(",") if v.strip()]
    dataset_path = os.getenv("BQ_DATASET_PATH")
    query_type = os.getenv("QUERY_TYPE", "aggregated")

    missing = [
        name for name, val in [
            ("EXPERIMENT_ID", experiment_id),
            ("START_DATE", start_date),
            ("END_DATE", end_date),
            ("VARIANTS", variants),
            ("BQ_DATASET_PATH", dataset_path),
        ] if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {missing}. "
            "Set them before running the pipeline."
        )

    # --- Extract ---
    logger.info("Extracting data from BigQuery...")
    bq_rows = fetch_bigquery_data(
        experiment_id=experiment_id,
        start_date=start_date,
        end_date=end_date,
        variants=variants,
        dataset_path=dataset_path,
        query_type=query_type,
    )

    experiment = transform_bq_rows_to_experiment_input(experiment_id, bq_rows)
    experiments = [experiment]

    # --- Transform (run statistical engines) ---
    final_payload = []

    freq_results = run_frequentist_pipeline(experiments)
    final_payload.extend(freq_results)

    bayes_results = run_bayesian_pipeline(experiments)
    final_payload.extend(bayes_results)

    # --- Load ---
    logger.info("Pushing all results to Airtable...")
    push_to_airtable(final_payload)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()

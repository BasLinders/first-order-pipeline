import logging
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
# OPERATIONAL PIPELINES
# ==========================================

def run_frequentist_pipeline(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("Starting Frequentist Pipeline...")
    engine = FrequentistEngine()
    results = []
    
    for row in rows:
        try:
            input_data = ExperimentInput(**row)
            # Replace with your actual frequentist method call
            stat_results = engine.run_analysis(data=input_data) 
            results.append({
                "experiment_id": row["experiment_id"],
                "engine": "frequentist",
                "results": [r.model_dump() for r in stat_results]
            })
        except Exception as e:
            logger.error(f"Frequentist Engine failed on {row.get('experiment_id')}: {e}")
            
    return results

def run_bayesian_pipeline(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("Starting Bayesian Pipeline...")
    engine = BayesianEngine()
    results = []
    
    for row in rows:
        try:
            input_data = ExperimentInput(**row)
            prob_results = engine.run_probability_analysis(data=input_data)
            
            # (Insert business case logic here if applicable)
            
            results.append({
                "experiment_id": row["experiment_id"],
                "engine": "bayesian",
                "results": [r.model_dump() for r in prob_results]
            })
        except Exception as e:
            logger.error(f"Bayesian Engine failed on {row.get('experiment_id')}: {e}")
            
    return results

# ==========================================
# PLACEHOLDER PIPELINES
# ==========================================

def run_behavioral_pipeline(rows): raise NotImplementedError("BehavioralEngine not yet deployed.")
def run_continuous_pipeline(rows): raise NotImplementedError("ContinuousMetricEngine not yet deployed.")
def run_interaction_pipeline(rows): raise NotImplementedError("InteractionEngine not yet deployed.")
def run_pretest_pipeline(rows): raise NotImplementedError("PretestEngine not yet deployed.")
def run_sequential_pipeline(rows): raise NotImplementedError("SequentialEngine not yet deployed.")
def run_srm_pipeline(rows): raise NotImplementedError("SRMEngine not yet deployed.")
def run_viz_pipeline(rows): raise NotImplementedError("VizEngine not yet deployed.")

# ==========================================
# MAIN ORCHESTRATOR
# ==========================================

def main():
    logger.info("Extracting data from BigQuery...")
    # bq_data = fetch_bigquery_data()
    bq_data = [{"experiment_id": "EXP_123", "visitors": [1000, 1000], "conversions": [100, 120]}] # Mock data
    
    final_payload = []
    
    # Example Routing Logic: Run both operational engines on the data
    # (Or filter bq_data based on what engine it needs)
    
    freq_results = run_frequentist_pipeline(bq_data)
    final_payload.extend(freq_results)
    
    bayes_results = run_bayesian_pipeline(bq_data)
    final_payload.extend(bayes_results)
    
    logger.info("Pushing all results to Airtable...")
    # push_to_airtable(final_payload)
    
    logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()

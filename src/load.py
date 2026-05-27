import os
import logging
from pyairtable import Api

logger = logging.getLogger(__name__)

def push_to_airtable(payload: list[dict]):
    logger.info("Initializing Airtable client...")
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    table_name = os.getenv("AIRTABLE_TABLE_NAME")
    
    if not all([api_key, base_id, table_name]):
        raise ValueError("Missing Airtable credentials in environment variables.")
        
    api = Api(api_key)
    table = api.table(base_id, table_name)
    
    # Format the payload to match Airtable's required schema
    airtable_records = []
    for item in payload:
        airtable_records.append({
            "fields": {
                "Experiment ID": item["experiment_id"],
                "Engine": item["engine"],
                # We can flatten specific metrics here instead of passing a raw string
                "Raw Results": str(item["results"]) 
            }
        })
        
    try:
        table.batch_create(airtable_records)
        logger.info(f"Successfully pushed {len(airtable_records)} records to Airtable.")
    except Exception as e:
        logger.error(f"Failed to push data to Airtable: {e}")
        raise

# first-order-pipeline
The pipeline orchestrator for First Order Engine.

## Repository structure
```text
first-order-pipeline/
│
├── Dockerfile                  # The build file we created earlier
├── requirements.txt            # Requires: google-cloud-bigquery, pyairtable
├── .gitignore                  
├── .dockerignore               # Prevents local credentials from entering the container
│
└── src/
    ├── __init__.py
    ├── extract.py              # BigQuery SQL execution
    ├── load.py                 # Airtable API interactions
    └── main.py                 # The execution script that ties it all together
```

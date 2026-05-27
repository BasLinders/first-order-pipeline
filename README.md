# First Order Pipeline

**First Order Pipeline** is the ETL orchestrator for [First Order Engine](https://github.com/BasLinders/first-order-engine). It handles everything that FOE deliberately does not: fetching experiment data from BigQuery, passing it to the statistical engines, and pushing the results to Airtable.

```
BigQuery  ──►  first-order-engine  ──►  Airtable
  (extract)        (transform)            (load)
```

FOE is a pure Python library — it has no opinion about data sources or destinations. This pipeline is one opinionated, production-ready integration built on top of it.

---

## Repository Structure

```text
first-order-pipeline/
│
├── main.py                          # Entry point — orchestrates the full ETL run
│
├── src/
│   ├── extract.py                   # BigQuery: runs parameterised GA4 queries
│   └── load.py                      # Airtable: batch-pushes results via pyairtable
│
├── tests/
│   ├── test_transform.py            # Unit tests for the BQ→ExperimentInput transform
│   ├── test_pipelines.py            # Unit tests for frequentist & Bayesian pipeline fns
│   └── test_main.py                 # Integration-level tests for the orchestrator
│
├── .github/
│   └── workflows/
│       ├── tests.yml                # Unit tests on Python 3.10–3.13 (on every push/PR)
│       ├── docker-build.yml         # Docker image build validation (on every push/PR)
│       └── pipeline-trigger.yml    # Manual dispatch + weekly cron to run the pipeline
│
├── Dockerfile                       # Container build for production runs
├── requirements.txt                 # Runtime dependencies (bigquery, pyairtable)
├── pyproject.toml                   # Pytest configuration
└── SECRETS_SETUP.md                 # Step-by-step guide to all required secrets
```

---

## How It Works

### 1. Extract
`src/extract.py` runs a parameterised BigQuery query against GA4 `events_*` tables. Two query types are supported:

- **`aggregated`** — returns one row per variant with visitor counts and conversion counts. Used for binomial (Frequentist / Bayesian) analysis.
- **`continuous`** — returns one row per converting user with revenue data. Used for continuous metric analysis.

### 2. Transform
`main.py` calls `transform_bq_rows_to_experiment_input()` to convert the per-variant BigQuery rows into an `ExperimentInput` object that FOE understands:

```python
# BigQuery output (one row per variant):
[
  {"experience_variant_label": "Control",    "visitors": 5000, "with_transaction": 500},
  {"experience_variant_label": "Variant_B",  "visitors": 5000, "with_transaction": 612},
]

# →  ExperimentInput (what FOE receives):
ExperimentInput(visitors=[5000, 5000], conversions=[500, 612], labels=["Control", "Variant_B"])
```

FOE's engines run and return structured result objects, which are serialised via `.model_dump()`.

### 3. Load
`src/load.py` formats the results and pushes them to an Airtable table via `batch_create()`.

---

## Running Locally

### Prerequisites
- Python 3.10+
- A virtual environment
- Access to `first-order-engine` (private GitHub repo — requires a PAT)
- Google Cloud credentials with BigQuery read access
- Airtable credentials

### Setup

```bash
# Clone and enter the repo
git clone https://github.com/BasLinders/first-order-pipeline.git
cd first-order-pipeline

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install runtime dependencies
pip install -r requirements.txt

# Install first-order-engine
pip install git+https://github.com/BasLinders/first-order-engine.git@main
```

### Configure environment variables

```bash
export EXPERIMENT_ID="EXP_001"
export START_DATE="2024-01-01"
export END_DATE="2024-01-31"
export VARIANTS="Control,Variant_B"
export BQ_DATASET_PATH="your-gcp-project.your_dataset"
export QUERY_TYPE="aggregated"           # or "continuous"
export AIRTABLE_API_KEY="your_key"
export AIRTABLE_BASE_ID="appXXXXXXXXXXXXXX"
export AIRTABLE_TABLE_NAME="Experiment Results"
```

Google Cloud credentials are picked up automatically from `gcloud auth application-default login` or from the `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to a service account JSON key.

### Run

```bash
python main.py
```

### Run the test suite

```bash
pip install pytest pytest-mock
pytest tests/
```

---

## Running via GitHub Actions

### Manual trigger (recommended for one-off runs)

1. Go to **Actions → Run Pipeline → Run workflow**
2. Fill in the form:
   - **Experiment ID** — e.g. `EXP_001`
   - **Start date** — e.g. `2024-01-01`
   - **End date** — e.g. `2024-01-31`
   - **Variants** — comma-separated, e.g. `Control,Variant_B`
   - **Query type** — `aggregated` or `continuous`
3. Click **Run workflow**

### Scheduled (automated weekly run)

The pipeline runs automatically every Monday at 06:00 UTC. It reads experiment config from the `DEFAULT_*` repository secrets (see `SECRETS_SETUP.md`).

---

## Required Secrets

All secrets are set at **Settings → Secrets and variables → Actions** in this repository. See [`SECRETS_SETUP.md`](./SECRETS_SETUP.md) for full instructions on how to obtain each value.

| Secret | Purpose |
|---|---|
| `FOE_GITHUB_TOKEN` | PAT to install `first-order-engine` (private repo) |
| `GCP_SA_KEY` | Service account JSON for BigQuery authentication |
| `BQ_DATASET_PATH` | BigQuery dataset path (`project.dataset`) |
| `AIRTABLE_API_KEY` | Airtable personal access token |
| `AIRTABLE_BASE_ID` | Airtable base ID (`appXXXXXXXXXXXXXX`) |
| `AIRTABLE_TABLE_NAME` | Airtable table name |
| `DEFAULT_EXPERIMENT_ID` | Default experiment for the weekly scheduled run |
| `DEFAULT_START_DATE` | Default start date for the weekly scheduled run |
| `DEFAULT_END_DATE` | Default end date for the weekly scheduled run |
| `DEFAULT_VARIANTS` | Default variants for the weekly scheduled run |

### Multiple clients

Each client has a separate GCP project. Store credentials per client and route by a `client` input in the workflow. See `SECRETS_SETUP.md` → section 6 for the full routing pattern.

---

## Adding a New Statistical Engine

`main.py` contains placeholder functions for engines not yet deployed. To activate one:

1. Import the engine from `foe`
2. Replace the `raise NotImplementedError` body with the actual call
3. Call it from `main()` and extend `final_payload`

Currently deployed: **Frequentist**, **Bayesian**  
Placeholders: Sequential, SRM, Interaction, Behavioral, Continuous, Pretest, Viz

---

## Relationship to First Order Engine

| | [first-order-engine](https://github.com/BasLinders/first-order-engine) | first-order-pipeline *(this repo)* |
|---|---|---|
| **Role** | Pure Python statistical library | ETL pipeline and infrastructure |
| **Knows about** | Math, models, inference | BigQuery, Airtable, Docker, CI/CD |
| **Installed as** | `pip install` dependency | Standalone service / container |
| **Has opinions about** | Statistical correctness | Data sources and destinations |

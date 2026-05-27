# GitHub Actions Secrets Setup — first-order-pipeline

All secrets live at:
**https://github.com/BasLinders/first-order-pipeline → Settings → Secrets and variables → Actions → New repository secret**

Secrets can be added at any time. Workflows that run before secrets exist will
simply fail — nothing breaks permanently.

---

## 1. FOE_GITHUB_TOKEN

Used by the Docker build to install `first-order-engine` from GitHub.

**How to get it:**
1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Name it `first-order-pipeline-docker`
4. Tick scope: **`public_repo`** (FOE repo is public)
5. Generate, copy immediately
6. Paste as secret value

---

## 2. GCP Service Account Keys (one per client)

Each client has a separate GCP project. Create one secret per client.

**Secret naming convention:**

| Secret name            | Contents                          |
|------------------------|-----------------------------------|
| `GCP_SA_KEY_CLIENT_A`  | Full JSON key for Client A's GCP  |
| `GCP_SA_KEY_CLIENT_B`  | Full JSON key for Client B's GCP  |
| *(add more as needed)* |                                   |

**How to get the JSON key per client:**
1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. Select the **client's** GCP project from the project switcher (top bar)
3. Find or create a service account with roles:
   - **BigQuery Data Viewer**
   - **BigQuery Job User**
4. Click the service account → **Keys** tab → **Add Key** → **Create new key** → **JSON**
5. Download the `.json` file, open it, paste the **entire JSON content** as the secret value

---

## 3. BigQuery Dataset Paths (one per client)

| Secret name                | Value format                          | Example                          |
|----------------------------|---------------------------------------|----------------------------------|
| `BQ_DATASET_PATH_CLIENT_A` | `gcp-project-id.dataset_name`         | `acme-analytics.ga4_export`      |
| `BQ_DATASET_PATH_CLIENT_B` | `gcp-project-id.dataset_name`         | `globex-data.ga4_raw`            |
| *(add more as needed)*     |                                       |                                  |

**Where to find the project ID:** GCP Console top bar (project switcher).
**Where to find the dataset name:** BigQuery → your project → dataset list.

---

## 4. Airtable Secrets (shared across clients, or per-client if separate bases)

| Secret name          | How to get it                                                                 |
|----------------------|-------------------------------------------------------------------------------|
| `AIRTABLE_API_KEY`   | https://airtable.com/create/tokens → create token with `data.records:write`  |
| `AIRTABLE_BASE_ID`   | Open the base in browser → URL contains `appXXXXXXXXXXXXXX` → that's the ID  |
| `AIRTABLE_TABLE_NAME`| Exact table name as it appears in Airtable, e.g. `Experiment Results`         |

---

## 5. Optional — Scheduled (cron) run defaults

The pipeline-trigger workflow runs every Monday at 06:00 UTC automatically.
Without these secrets the scheduled run will raise an EnvironmentError and stop.

| Secret name              | Example value       |
|--------------------------|---------------------|
| `DEFAULT_EXPERIMENT_ID`  | `EXP_001`           |
| `DEFAULT_START_DATE`     | `2024-01-01`        |
| `DEFAULT_END_DATE`       | `2024-01-31`        |
| `DEFAULT_VARIANTS`       | `Control,Variant_B` |

---

## 6. How the multi-client routing works in the workflow

When triggering the pipeline manually via GitHub Actions UI, you fill in a
`client` field (e.g. `client_a`). The workflow maps that to the right secrets:

```yaml
- name: Set client credentials
  run: |
    case "${{ github.event.inputs.client }}" in
      client_a)
        echo "GCP_SA_KEY=${{ secrets.GCP_SA_KEY_CLIENT_A }}" >> $GITHUB_ENV
        echo "BQ_DATASET_PATH=${{ secrets.BQ_DATASET_PATH_CLIENT_A }}" >> $GITHUB_ENV
        ;;
      client_b)
        echo "GCP_SA_KEY=${{ secrets.GCP_SA_KEY_CLIENT_B }}" >> $GITHUB_ENV
        echo "BQ_DATASET_PATH=${{ secrets.BQ_DATASET_PATH_CLIENT_B }}" >> $GITHUB_ENV
        ;;
      *)
        echo "Unknown client: ${{ github.event.inputs.client }}"
        exit 1
        ;;
    esac
```

**NOTE:** The `pipeline-trigger.yml` in the repo does not yet include this
multi-client routing. When ready to add clients, update the workflow with the
`client` input field and the `case` block above, and update
`google-github-actions/auth` to use `${{ env.GCP_SA_KEY }}`.

---

## Summary checklist

- [ ] `FOE_GITHUB_TOKEN` — GitHub PAT (public_repo scope)
- [ ] `GCP_SA_KEY_<CLIENT>` — one per client GCP project
- [ ] `BQ_DATASET_PATH_<CLIENT>` — one per client dataset
- [ ] `AIRTABLE_API_KEY`
- [ ] `AIRTABLE_BASE_ID`
- [ ] `AIRTABLE_TABLE_NAME`
- [ ] `DEFAULT_*` secrets (only needed for scheduled Monday runs)
- [ ] Update `pipeline-trigger.yml` with multi-client `client` input + case routing

# Sample RAG: Society Documents

This demo shows one RAG path end to end: extract two society documents, create
embeddings, store them in Chroma, retrieve relevant passages for a question,
and return an AI answer with page/row citations.

The included agenda and expense sheet are small, fictional examples created for
this demo. They contain no real society or personal data.

```text
documents/AGM PDF ── text/OCR ─┐
                               ├─ chunks + embeddings ─ Chroma ─ /ask + chat page
documents/expense workbook ────┘
```

It is intentionally public and has no user authentication. Use only demo data.

## What is in the repository

| Path | Purpose |
| --- | --- |
| `demo.py` | Ingestion, OCR, retrieval API, and inline chat page |
| `documents/` | Two small, fictional sample documents committed for learners |
| `chroma_db/` | Generated vector index; created by ingestion and ignored by Git |
| `requirements.txt` | Runtime packages used by local serving and Cloud Run |

## Run locally

### Prerequisites

- Python 3.12
- An OpenAI API key with API access and billing enabled. Ingestion and each
  question make paid API calls.
- A model available to your OpenAI account. This demo defaults to
  `gpt-5.4-mini` in `demo.py` for OCR and chat completion, but model names and
  availability vary by account and API version. If you receive a model-not-found
  error, change `CHAT_MODEL` in `demo.py` to a model enabled for your key.
- Only one environment variable is used: `SOCIETY_GENIE_OPENAI_API_KEY`. The old
  role-token variables are not needed for this demo.

### 1. Install the app dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Configure the API key and build the index

The repository includes these two fictional sample files:

| File | Content |
| --- | --- |
| `sample_agenda.pdf` | One-page, selectable-text AGM agenda |
| `sample_expenses.xlsx` | Three fictional expense records |

Copy `.env.example` to `.env`, then replace the placeholder with your key.
Keep `.env` local; it is excluded from Git.

```dotenv
SOCIETY_GENIE_OPENAI_API_KEY=your-key
```

If your OpenAI account does not support the default model in `demo.py`, edit
`CHAT_MODEL` near the top of the file to a model available to your project.
Build the Chroma index:

```powershell
.\.venv\Scripts\python.exe demo.py ingest
```

**Ingestion is required before serving.** It extracts the agenda text and
expense rows, then makes paid embedding API calls to build the index. The sample
PDF is text-based, so it does not need vision OCR; scanned PDFs use the OCR
fallback. Running ingestion again repeats embedding calls; run it once unless
you intentionally want to rebuild the index. The generated Chroma index is
stored in `sample-rag-society/chroma_db/` (relative to the `gcp-labs` repo
root); this folder is local build output and is excluded from Git.

### 3. Start the chat demo

```powershell
.\.venv\Scripts\python.exe demo.py serve --port 8000
```

Open <http://localhost:8000/> and ask questions. `GET /health` shows the
number of indexed chunks; interactive API docs are at <http://localhost:8000/docs>.
Each live question also makes embedding and chat-completion API calls. If the
server returns a model error, confirm the model in `demo.py` is enabled for your
OpenAI key and restart the app.

### 4. Try these questions

- “When is the sample AGM, and what topics are on its agenda?”
- “What amount is recorded for the BrightPath lift inspection?”
- “Which spreadsheet row supports the garden maintenance expense?”
- “What is the purpose of the annual governance review item on the agenda?”

The workbook has a few fictional example rows. Retrieval finds relevant rows; it
does not run SQL or calculate complete financial totals.

### Optional: call the API directly

With the server running, in PowerShell:

```powershell
$body = @{ question = "When is the sample AGM, and what topics are on its agenda?" } |
    ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/ask" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

The response contains an `answer` and a `sources` array with the filename and
PDF page or workbook sheet/row.

## Deploy the demo to Cloud Run

The following commands use PowerShell. Replace the project ID and keep it
explicit in commands so you do not deploy to the wrong project:

```powershell
$PROJECT_ID = "YOUR_PROJECT_ID"
gcloud config set project $PROJECT_ID
```

1. Enable the required APIs:

   ```powershell
   gcloud services enable `
       run.googleapis.com `
       artifactregistry.googleapis.com `
       cloudbuild.googleapis.com `
       secretmanager.googleapis.com `
       --project=$PROJECT_ID
   ```

2. Create an Artifact Registry Docker repository:

   ```powershell
   gcloud artifacts repositories create sample-rag-society `
       --repository-format=docker `
       --location=us-central1 `
       --project=$PROJECT_ID
   ```

3. Create a **new, demo-only** Secret Manager secret named
   `SAMPLE_RAG_SOCIETY_OPENAI_API_KEY` and store your OpenAI key as its latest
   version. Do not reuse an existing secret: this lets cleanup safely delete
   only the secret created for this demo. Get the project number and grant its
   default Compute Engine service account access to the new secret:

   ```powershell
   gcloud secrets create SAMPLE_RAG_SOCIETY_OPENAI_API_KEY `
       --replication-policy=automatic `
       --project=$PROJECT_ID
   # Add the key as a new secret version using the Cloud Console:
   # Secret Manager > SAMPLE_RAG_SOCIETY_OPENAI_API_KEY > Add new version.
   $PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
   $RUNTIME_SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
   gcloud secrets add-iam-policy-binding SAMPLE_RAG_SOCIETY_OPENAI_API_KEY `
       --member="serviceAccount:$RUNTIME_SA" `
       --role="roles/secretmanager.secretAccessor" `
       --project=$PROJECT_ID
   ```
4. Build the index locally using the steps above.
5. Build and deploy the image:

   ```powershell
   gcloud builds submit `
       --project=$PROJECT_ID `
       --tag "us-central1-docker.pkg.dev/$PROJECT_ID/sample-rag-society/sample-rag-society-demo" `
       .
   gcloud run deploy sample-rag-society `
       --image "us-central1-docker.pkg.dev/$PROJECT_ID/sample-rag-society/sample-rag-society-demo" `
       --region us-central1 `
       --project=$PROJECT_ID `
       --allow-unauthenticated `
       --min-instances=0 `
       --max-instances=1 `
       --set-secrets "SOCIETY_GENIE_OPENAI_API_KEY=SAMPLE_RAG_SOCIETY_OPENAI_API_KEY:latest"
   ```

The image contains `demo.py` and the generated `chroma_db/`, not the source
documents or `.env`. The service is public and can spend against your OpenAI
key; use demo data, monitor usage, and run the cleanup below immediately after
the demo. Match the `CHAT_MODEL` in `demo.py` to a model available to your
organization before deploying.

## Clean up after the demo

Run this after you finish. Review `$PROJECT_ID`; these commands delete the
Cloud Run service, Artifact Registry repository, and dedicated secret created
by this demo.

```powershell
# Remove this demo's public Cloud Run service.
gcloud run services delete sample-rag-society `
    --region=us-central1 --project=$PROJECT_ID --quiet

# Remove the container image repository created for this demo.
gcloud artifacts repositories delete sample-rag-society `
    --location=us-central1 --project=$PROJECT_ID --quiet

# Remove the access grant added during deployment, then delete this demo's
# dedicated secret. Do not delete or change any secret used by another app.
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
$RUNTIME_SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud secrets remove-iam-policy-binding SAMPLE_RAG_SOCIETY_OPENAI_API_KEY `
    --member="serviceAccount:$RUNTIME_SA" `
    --role="roles/secretmanager.secretAccessor" `
    --project=$PROJECT_ID --quiet
gcloud secrets delete SAMPLE_RAG_SOCIETY_OPENAI_API_KEY `
    --project=$PROJECT_ID --quiet
```

Verify the resources created by this deployment have been removed:

```powershell
gcloud run services list --region=us-central1 --project=$PROJECT_ID
gcloud artifacts repositories list --location=us-central1 --project=$PROJECT_ID
gcloud secrets list --project=$PROJECT_ID
```

Confirm that `sample-rag-society` is absent from the service and repository
lists, and `SAMPLE_RAG_SOCIETY_OPENAI_API_KEY` is absent from the secret list.

The deployment enables Google Cloud APIs but does not create them as billable
resources; this guide leaves them enabled because other workloads in a project
may use them. It also does not delete the project or any unrelated resources.
Therefore, this cleanup removes this demo's deployed resources, but cannot
guarantee zero charges for the whole project. Check the project's Billing
reports for any remaining usage. Deleting the Secret Manager secret does not
revoke the OpenAI API key; revoke it in your OpenAI account if you will no
longer use it.
